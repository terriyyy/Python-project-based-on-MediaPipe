import cv2
import numpy as np
import mediapipe as mp
import time
import math
import random
import traceback

class GestureDrawAdapter:
    """A gesture drawing game adapter for browser.
    - Consistent with other adapters in the project: provides process(frame) to return the processed frame
    - Supports start_game() interface to be called by backend /api/start_game
    """
    def __init__(self, time_limit=60):
        self.width = 1280
        self.height = 720
        self.time_limit = time_limit
        self.score = 0
        self.start_time = None
        self.state = 'WAIT'  # WAIT -> PLAYING -> END

        # MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.6)
        self.mp_draw = mp.solutions.drawing_utils

        # canvas (white background)
        self.canvas = np.full((self.height, self.width, 3), 255, dtype=np.uint8)

        # drawing
        self.current_stroke = []
        self.strokes = []

        # target shape
        self.target = self._random_target()
        # initialize guide hit flags to match initial target
        self.guide_hit_flags = [False] * len(self.target.get('guide_points', []))

        # UI colors
        self.c_ui_bg = (60, 60, 80)
        self.c_text_accent = (0, 200, 255)
        self.c_border = (100, 100, 140)

        # preview pip
        self.pip_scale = 0.25

        # guide/visit tracking: index of next guide point (player should hit in order)
        self.next_guide_idx = 0
        self.guide_hit_flags = []

    def start_game(self):
        self.start_time = time.time()
        self.state = 'PLAYING'
        self.score = 0
        self.canvas[:] = 255
        self.current_stroke = []
        self.strokes = []
        self.target = self._random_target()
        # reset guide tracking
        self.next_guide_idx = 0
        self.guide_hit_flags = [False] * len(self.target.get('guide_points', []))

    def _random_target(self):
        # Limit the target center to the central area of the screen, prompting players to draw near the center
        shape = random.choice(['circle', 'square', 'triangle', 'star'])
        cx = random.randint(int(self.width*0.35), int(self.width*0.65))
        cy = random.randint(int(self.height*0.35), int(self.height*0.65))
        size = random.randint(70, 120)
        pts = self._shape_points(shape, (cx, cy), size, n=120)
        # Generate a few key points (3-6) for the player to connect in order
        guide_count = random.choice([3, 4, 5, 6])
        idxs = np.linspace(0, len(pts)-1, guide_count, dtype=int)
        guide_points = pts[idxs]
        return {'shape': shape, 'center': (cx, cy), 'size': size, 'points': pts, 'guide_points': guide_points}

    def _shape_points(self, shape, center, size, n=120):
        cx, cy = center
        t = np.linspace(0, 2*math.pi, n, endpoint=False)
        if shape == 'circle':
            pts = np.vstack((cx + size*np.cos(t), cy + size*np.sin(t))).T
        elif shape == 'square':
            seg = n // 4
            pts = []
            half = size
            corners = [(cx-half, cy-half), (cx+half, cy-half), (cx+half, cy+half), (cx-half, cy+half)]
            for i in range(4):
                x0,y0 = corners[i]
                x1,y1 = corners[(i+1)%4]
                for k in range(seg):
                    a = k/seg
                    pts.append((int(x0 + (x1-x0)*a), int(y0 + (y1-y0)*a)))
            pts = np.array(pts)
        elif shape == 'triangle':
            pts = []
            for i in range(3):
                angle0 = i*2*math.pi/3 - math.pi/2
                angle1 = (i+1)*2*math.pi/3 - math.pi/2
                for a in np.linspace(angle0, angle1, n//3, endpoint=False):
                    pts.append((int(cx + size*math.cos(a)), int(cy + size*math.sin(a))))
            pts = np.array(pts)
        elif shape == 'star':
            pts = []
            for i in range(n):
                angle = 2*math.pi*i/n
                r = size if i%2==0 else size*0.45
                pts.append((int(cx + r*math.cos(angle)), int(cy + r*math.sin(angle))))
            pts = np.array(pts)
        else:
            pts = np.zeros((n,2), dtype=int)
        return pts.astype(int)

    def _resample(self, pts, n=120):
        if len(pts) < 2:
            return np.zeros((n,2))
        pts = np.array(pts, dtype=float)
        d = np.sqrt(((np.diff(pts, axis=0))**2).sum(axis=1))
        d = np.insert(d, 0, 0.0)
        ds = d.cumsum()
        if ds[-1] == 0:
            return np.tile(pts[0], (n,1))
        t = np.linspace(0, ds[-1], n)
        res = []
        for ti in t:
            idx = np.searchsorted(ds, ti)
            if idx == 0:
                res.append(pts[0])
            elif idx >= len(pts):
                res.append(pts[-1])
            else:
                a = (ti - ds[idx-1]) / (ds[idx] - ds[idx-1] + 1e-8)
                res.append(pts[idx-1]*(1-a) + pts[idx]*a)
        return np.array(res)

    def _score_stroke_vs_target(self, stroke, target):
        if len(stroke) < 10:
            return 0.0
        s_pts = self._resample(stroke, n=120)
        t_pts = self._resample(target['points'], n=120)
        def avg_min(a,b):
            d = np.sqrt(((a[:,None,:] - b[None,:,:])**2).sum(axis=2))
            return d.min(axis=1).mean()
        d1 = avg_min(s_pts, t_pts)
        d2 = avg_min(t_pts, s_pts)
        d = (d1 + d2)/2.0
        norm = max(1.0, target['size'])
        score_raw = max(0.0, 1.0 - d / (norm * 0.8))
        # Additional guide point matching score (if guide_points are provided)
        guide_score = 0.0
        if 'guide_points' in target and len(target['guide_points']) > 0:
            gp = np.array(target['guide_points'], dtype=float)
            # Calculate the average nearest point distance from guide points to stroke
            sp = np.array(stroke, dtype=float)
            if len(sp) > 0:
                d_gp = np.sqrt(((gp[:,None,:] - sp[None,:,:])**2).sum(axis=2))
                min_d = d_gp.min(axis=1).mean()
                guide_score = max(0.0, 1.0 - min_d / (norm * 0.7))

        # Final score: higher weight on guide point matching, shape similarity as a supplement
        final_score = 0.65 * guide_score + 0.35 * score_raw
        return final_score

    def _check_and_mark_guides(self, stroke):
        """Check if the current stroke is close to the next guide point (in order).
        Return how many new guides were hit (usually 0 or 1)."""
        if 'guide_points' not in self.target or len(self.target['guide_points']) == 0:
            return 0
        added = 0
        gp = np.array(self.target['guide_points'], dtype=float)
        sp = np.array(stroke, dtype=float)
        if len(sp) == 0:
            return 0
        # Allow detection for the next few points (to prevent quick skipping)
        max_check = 2
        for attempt in range(max_check):
            idx = self.next_guide_idx
            if idx >= len(gp):
                break
            # Calculate the minimum distance from any point in the stroke to the guide
            d = np.sqrt(((sp - gp[idx])**2).sum(axis=1)).min()
            # Threshold: reference to target size, slightly relaxed
            thresh = max(30.0, self.target['size'] * 0.25)
            if d <= thresh:
                # mark hit
                self.guide_hit_flags[idx] = True
                self.next_guide_idx += 1
                added += 1
            else:
                break
        return added

    def draw_overlay(self, frame):
        overlay = frame.copy()
        pts = self.target['points']
        cv2.polylines(overlay, [pts], isClosed=True, color=(0,140,255), thickness=4)
        cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)
        cv2.polylines(frame, [pts], isClosed=True, color=(0,120,200), thickness=2)

        # history strokes
        for stroke in self.strokes:
            if len(stroke) > 1:
                cv2.polylines(frame, [np.array(stroke, dtype=int)], isClosed=False, color=(200,200,255), thickness=5)
        # current stroke
        if len(self.current_stroke) > 1:
            cv2.polylines(frame, [np.array(self.current_stroke, dtype=int)], isClosed=False, color=(255,180,20), thickness=6)

        # Draw guide points (numbered), green if hit, orange if not
        if 'guide_points' in self.target:
            for i, (gx, gy) in enumerate(self.target['guide_points']):
                hit = False
                if i < len(self.guide_hit_flags):
                    hit = self.guide_hit_flags[i]
                color = (0,200,0) if hit else (0,140,255)
                cv2.circle(frame, (int(gx), int(gy)), 14 if not hit else 12, color, -1)
                cv2.putText(frame, str(i+1), (int(gx)+14, int(gy)+8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30,30,30), 2)

        # HUD text (English): instruct players to connect guide points and show score/time
        elapsed = 0 if not self.start_time else time.time() - self.start_time
        left = max(0, int(self.time_limit - elapsed))
        cv2.putText(frame, f"Target: {self.target['shape']}", (20,30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,200,200), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Score: {int(self.score)}", (20,60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200,200,0), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Time left: {left}s", (self.width-220,30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200,180,180), 2, cv2.LINE_AA)
        cv2.putText(frame, "Connect the numbered guide points in order (draw near center)", (20, self.height-30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (120,120,120), 2, cv2.LINE_AA)
        return frame

    def count_fingers(self, lm):
        pts = lm.landmark
        fingers = []
        if pts[4].x < pts[3].x: fingers.append(1)
        else: fingers.append(0)
        for id in [8, 12, 16, 20]:
            if pts[id].y < pts[id-2].y: fingers.append(1)
            else: fingers.append(0)
        total = sum(fingers)
        # thumb correction
        if abs(pts[4].x - pts[3].x) < 0.02:
            if fingers[0] == 1: total -= 1
        return total

    def process(self, frame):
        try:
            frame = cv2.resize(frame, (self.width, self.height))
            if self.state != 'PLAYING':
                # show onboarding screen (English)
                white = self.canvas.copy()
                cv2.putText(white, "Gesture Draw", (self.width//2 - 220, self.height//2 - 40), cv2.FONT_HERSHEY_DUPLEX, 2.0, (50,50,50), 3)
                cv2.putText(white, "Press Start to begin. Connect the numbered guide points in order and draw near the center.", (60, self.height//2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80,80,80), 2)
                return white

            # process hands
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)

            pip_w, pip_h = int(self.width*self.pip_scale), int(self.height*self.pip_scale)
            frame_small = cv2.resize(frame, (pip_w, pip_h))

            index_up = False
            middle_up = False

            if results.multi_hand_landmarks:
                lm = results.multi_hand_landmarks[0]
                # simple up detection
                def is_up(tip, pip):
                    return lm.landmark[tip].y < lm.landmark[pip].y
                index_up = is_up(8,6)
                middle_up = is_up(12,10)
                ix = int(lm.landmark[8].x * self.width)
                iy = int(lm.landmark[8].y * self.height)
                cv2.circle(frame, (ix, iy), 8, (0,255,0) if index_up else (0,120,0), -1)

                # draw mode: index up, middle down
                if index_up and not middle_up:
                    self.current_stroke.append((ix, iy))
                    # 检查是否命中下一关键点（在绘制过程中）
                    self._check_and_mark_guides(self.current_stroke)
                else:
                    # finish stroke
                    if len(self.current_stroke) > 5:
                        # 主要根据关键点命中情况计分：每命中一个关键点得基础分
                        hits = sum(1 for f in self.guide_hit_flags if f)
                        total = len(self.guide_hit_flags) if len(self.guide_hit_flags)>0 else 1
                        # 基础分：每个关键点 30 分，全部命中额外奖励 40 分
                        gained = int(hits * 30 + (40 if hits == total else 0))
                        self.score += gained
                        self.strokes.append(self.current_stroke.copy())
                        self.current_stroke = []
                        # 如果全部命中则切换目标并重置 guide flags
                        if hits == total:
                            # Completed current target: clear canvas and prepare next target
                            self.canvas[:] = 255
                            self.strokes = []
                            self.current_stroke = []
                            self.target = self._random_target()
                            self.next_guide_idx = 0
                            self.guide_hit_flags = [False] * len(self.target.get('guide_points', []))
                        else:
                            # 保留当前 target，但不重复计分（已计入 score）
                            self.next_guide_idx = sum(1 for f in self.guide_hit_flags if f)
                    else:
                        self.current_stroke = []

                # clear canvas: all fingers up
                finger_count = self.count_fingers(lm)
                if finger_count >= 4:
                    self.canvas[:] = 255
                    self.strokes = []
                    self.current_stroke = []

            else:
                # no hand: finalize stroke
                if len(self.current_stroke) > 0:
                    if len(self.current_stroke) > 5:
                        hits = sum(1 for f in self.guide_hit_flags if f)
                        total = len(self.guide_hit_flags) if len(self.guide_hit_flags)>0 else 1
                        gained = int(hits * 30 + (40 if hits == total else 0))
                        self.score += gained
                        self.strokes.append(self.current_stroke.copy())
                        self.current_stroke = []
                        if hits == total:
                            # Completed current target: clear canvas and load next
                            self.canvas[:] = 255
                            self.strokes = []
                            self.current_stroke = []
                            self.target = self._random_target()
                            self.next_guide_idx = 0
                            self.guide_hit_flags = [False] * len(self.target.get('guide_points', []))
                        else:
                            self.next_guide_idx = sum(1 for f in self.guide_hit_flags if f)
                    else:
                        self.current_stroke = []

            # composite final view
            final_view = self.canvas.copy()
            # draw strokes
            for stroke in self.strokes:
                if len(stroke) > 1:
                    cv2.polylines(final_view, [np.array(stroke, dtype=int)], isClosed=False, color=(220,220,255), thickness=6)
            if len(self.current_stroke) > 1:
                cv2.polylines(final_view, [np.array(self.current_stroke, dtype=int)], isClosed=False, color=(255,200,50), thickness=8)

            # overlay target & HUD
            final_view = self.draw_overlay(final_view)

            # pip-inset
            x_off = self.width - pip_w - 20
            y_off = self.height - pip_h - 20
            cv2.rectangle(final_view, (x_off-4, y_off-4), (x_off+pip_w+4, y_off+pip_h+4), self.c_border, -1)
            final_view[y_off:y_off+pip_h, x_off:x_off+pip_w] = frame_small

            # end condition
            if self.start_time and (time.time() - self.start_time > self.time_limit):
                # show end screen overlay
                cv2.rectangle(final_view, (0,0), (self.width, self.height), (20,20,20), -1)
                cv2.putText(final_view, f"Game Over Score: {int(self.score)}", (self.width//2 - 300, self.height//2), cv2.FONT_HERSHEY_DUPLEX, 2.0, (220,220,220), 3)
                self.state = 'END'

            return final_view
        except Exception as e:
            print(f"[GestureDraw] error: {e}")
            traceback.print_exc()
            return frame

    def __del__(self):
        try:
            if hasattr(self, 'hands'):
                self.hands.close()
        except Exception:
            pass
