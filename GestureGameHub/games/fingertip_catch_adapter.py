import cv2
import numpy as np
import mediapipe as mp
import random
import time
import math
import traceback

class FingertipCatchAdapter:
    """Fingertip Catch Stars game adapter.
    - Use MediaPipe Hands to track index fingertip (landmark 8) as the catcher.
    - Stars spawn at top and fall; catching a star gives points; missed star costs a life.
    """
    def __init__(self, width=1280, height=720, time_limit=9999):
        self.width = width
        self.height = height
        self.time_limit = time_limit
        self.state = 'WAIT'  # WAIT, PLAYING, END
        self.start_time = None
        self.score = 0
        self.lives = 3
        self.level = 1
        self.base_speed = 3.0

        # MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.6)
        self.mp_draw = mp.solutions.drawing_utils

        # stars list
        self.stars = []  # each star: dict x,y,vy,size,alive
        self.max_stars = 1
        self.max_stars_cap = 12
        # spawn control
        self.last_spawn_time = 0.0
        self.spawn_interval = 1.0  # seconds between spawns (will reduce with difficulty)

        # restart button control (for END state)
        self.last_restart_touch_time = 0.0
        self.restart_cooldown = 1.0  # seconds to avoid immediate double-restart
        self.restart_btn_w = int(self.width * 0.28)
        self.restart_btn_h = 64

        # visuals
        # create a vertical gradient background and some faint static background stars
        self.bg = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        top_color = np.array((12, 18, 30), dtype=np.uint8)
        bottom_color = np.array((35, 55, 90), dtype=np.uint8)
        for y in range(self.height):
            t = y / max(1, (self.height-1))
            col = (top_color * (1-t) + bottom_color * t).astype(np.uint8)
            self.bg[y, :, :] = col
        # ambient tiny stars (positions and brightness)
        self.bg_stars = []
        for i in range(120):
            sx = random.randint(0, self.width-1)
            sy = random.randint(0, self.height-1)
            b = random.randint(10, 40)
            self.bg_stars.append((sx, sy, b))
        for sx, sy, b in self.bg_stars:
            cv2.circle(self.bg, (sx, sy), 1, (b, b, b), -1)

    def start_game(self):
        self.state = 'PLAYING'
        self.start_time = time.time()
        self.score = 0
        self.lives = 3
        self.level = 1
        self.base_speed = 3.0
        self.stars = []
        self._spawn_star()

    def _spawn_star(self):
        # spawn a single star at a random x near top
        size = random.randint(24, 40)
        # spawn nearer to center horizontally because edges may not detect the hand well
        x_min = int(self.width * 0.15) + size + 10
        x_max = int(self.width * 0.85) - size - 10
        x = random.randint(max(size + 10, x_min), min(self.width - size - 10, x_max))
        y = -size - random.randint(0, 100)
        # factor in elapsed time and score to make falling speed gradually increase
        elapsed = 0.0 if not self.start_time else (time.time() - self.start_time)
        time_speed = (elapsed // 15) * 0.35  # small speed bump every 15s
        score_speed = (self.score // 50) * 0.5
        vy = self.base_speed + random.random() * 1.2 + score_speed + time_speed
        self.stars.append({'x': float(x), 'y': float(y), 'vy': float(vy), 'size': int(size), 'alive': True})

    def _draw_star(self, img, cx, cy, r, color=(0,200,255)):
        # draw a simple 5-point star
        pts = []
        for i in range(10):
            angle = i * math.pi / 5 - math.pi/2
            rad = r if i % 2 == 0 else r*0.45
            x = int(cx + rad * math.cos(angle))
            y = int(cy + rad * math.sin(angle))
            pts.append((x,y))
        cv2.fillPoly(img, [np.array(pts, dtype=np.int32)], color)
        cv2.polylines(img, [np.array(pts, dtype=np.int32)], True, (20,120,200), 2)

    def process(self, frame):
        try:
            frame = cv2.resize(frame, (self.width, self.height))
            view = frame.copy()

            # If waiting for start, show onboarding and return early (no hand processing)
            if self.state == 'WAIT':
                tmp = self.bg.copy()
                cv2.putText(tmp, "Fingertip Catch Stars", (self.width//2 - 300, self.height//2 - 40), cv2.FONT_HERSHEY_DUPLEX, 2.0, (200,200,220), 3)
                cv2.putText(tmp, "Press Start to begin. Use your index fingertip to catch falling stars.", (80, self.height//2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (180,180,200), 2)
                # small camera pip
                pip = cv2.resize(view, (int(self.width*0.25), int(self.height*0.25)))
                ph, pw = pip.shape[:2]
                tmp[20:20+ph, 20:20+pw] = pip
                return tmp

            # process hands for both PLAYING and END states (so we can detect restart touches)
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)

            # default fingertip position center bottom
            fx, fy = self.width//2, int(self.height*0.75)
            hand_present = False
            index_up = False
            middle_up = False
            lm = None
            if results and getattr(results, 'multi_hand_landmarks', None):
                hand_present = True
                for lm_ in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(view, lm_, self.mp_hands.HAND_CONNECTIONS)
                lm = results.multi_hand_landmarks[0]
                fx = int(lm.landmark[8].x * self.width)
                fy = int(lm.landmark[8].y * self.height)
                # simple up detection used elsewhere
                def is_up(tip, pip):
                    return lm.landmark[tip].y < lm.landmark[pip].y
                index_up = is_up(8,6)
                middle_up = is_up(12,10)
                cv2.circle(view, (fx, fy), 10, (0,255,0), -1)

            # update stars
            for s in self.stars:
                if not s['alive']: continue
                s['y'] += s['vy']

            # collision detection
            caught_any = []
            for s in list(self.stars):
                if not s['alive']: continue
                dx = s['x'] - fx
                dy = s['y'] - fy
                dist = math.hypot(dx, dy)
                if dist <= s['size'] + 18 and hand_present:
                    # caught
                    s['alive'] = False
                    self.score += 10
                    # increase difficulty every 50 points
                    self.level = 1 + (self.score // 50)
                    self.base_speed = 3.0 + (self.level-1) * 0.6
                    caught_any.append(s)
                elif s['y'] - s['size'] > self.height:
                    # missed
                    s['alive'] = False
                    self.lives -= 1

            # remove dead and spawn to maintain up to max_stars
            self.stars = [s for s in self.stars if s['alive']]
            # dynamically adjust difficulty: increase max stars over time and score
            elapsed = 0.0 if not self.start_time else (time.time() - self.start_time)
            time_factor = int(elapsed // 10)  # every 10s allow one more star
            score_factor = int(self.score // 30)  # every 30 points add a star
            target_max = min(self.max_stars_cap, 1 + time_factor + score_factor)
            self.max_stars = max(1, target_max)
            # spawn interval shortens as level/score increases
            self.spawn_interval = max(0.25, 1.0 - min(0.7, (self.score // 50) * 0.08 + (time_factor * 0.02)))
            # spawn gradually based on spawn_interval
            now = time.time()
            while len(self.stars) < self.max_stars and (now - self.last_spawn_time) >= self.spawn_interval:
                self._spawn_star()
                self.last_spawn_time = now
                now = time.time()

            # draw onto gradient background, then blend camera view faintly
            overlay = self.bg.copy()
            for s in self.stars:
                self._draw_star(overlay, int(s['x']), int(s['y']), s['size'], color=(0,220,220))

            # HUD
            cv2.putText(overlay, f"Score: {self.score}", (20,40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (220,220,0), 2)
            cv2.putText(overlay, f"Lives: {self.lives}", (20,80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,220,50), 2)
            cv2.putText(overlay, f"Level: {self.level}", (20,120), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200,200,200), 2)

            # small pip camera
            pip = cv2.resize(frame, (int(self.width*0.2), int(self.height*0.2)))
            ph, pw = pip.shape[:2]
            overlay[self.height-ph-20:self.height-20, 20:20+pw] = pip

            # composite
            final = cv2.addWeighted(overlay, 0.9, view, 0.1, 0)

            # If lives exhausted, set END state and show overlay + restart button
            if self.lives <= 0 and self.state != 'END':
                self.state = 'END'

            if self.state == 'END':
                # dark overlay and big score
                cv2.rectangle(final, (0,0), (self.width, self.height), (10,10,10), -1)
                cv2.putText(final, f"Game Over", (self.width//2 - 180, self.height//2 - 40), cv2.FONT_HERSHEY_DUPLEX, 2.0, (240,240,240), 3)
                cv2.putText(final, f"Score: {self.score}", (self.width//2 - 150, self.height//2 + 20), cv2.FONT_HERSHEY_DUPLEX, 1.6, (240,240,240), 3)
                # draw restart button near bottom center
                btn_w = self.restart_btn_w
                btn_h = self.restart_btn_h
                btn_x = (self.width - btn_w) // 2
                btn_y = self.height - btn_h - 24
                cv2.rectangle(final, (btn_x, btn_y), (btn_x + btn_w, btn_y + btn_h), (40,120,200), -1)
                cv2.putText(final, "RESTART", (btn_x + 30, btn_y + btn_h//2 + 10), cv2.FONT_HERSHEY_DUPLEX, 1.2, (230,230,230), 2)

                # detect fingertip touching the restart button
                try:
                    if hand_present and lm is not None:
                        # check fingertip coordinates (accept any fingertip presence over button)
                        over_btn = (btn_x <= fx <= btn_x + btn_w and btn_y <= fy <= btn_y + btn_h)
                        # visual feedback: highlight button when fingertip is over it
                        if over_btn:
                            cv2.rectangle(final, (btn_x, btn_y), (btn_x + btn_w, btn_y + btn_h), (80,160,240), -1)
                            cv2.putText(final, "RESTART", (btn_x + 30, btn_y + btn_h//2 + 10), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255,255,255), 2)
                            cv2.circle(final, (fx, fy), 12, (255,220,100), -1)
                        now = time.time()
                        if over_btn and (now - self.last_restart_touch_time > self.restart_cooldown):
                            # restart the game
                            self.start_game()
                            self.last_restart_touch_time = now
                except Exception:
                    pass

            return final
        except Exception as e:
            print(f"[FingertipCatch] error: {e}")
            traceback.print_exc()
            return frame

    def __del__(self):
        try:
            if hasattr(self, 'hands'):
                self.hands.close()
        except Exception:
            pass
