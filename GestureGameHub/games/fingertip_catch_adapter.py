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

        # visuals
        self.bg = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.bg[:] = (20, 24, 30)

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
        x = random.randint(size + 10, self.width - size - 10)
        y = -size - random.randint(0, 100)
        vy = self.base_speed + random.random() * 1.2 + (self.score // 50) * 0.5
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

            if self.state != 'PLAYING':
                # onboarding screen
                tmp = self.bg.copy()
                cv2.putText(tmp, "Fingertip Catch Stars", (self.width//2 - 300, self.height//2 - 40), cv2.FONT_HERSHEY_DUPLEX, 2.0, (200,200,220), 3)
                cv2.putText(tmp, "Press Start to begin. Use your index fingertip to catch falling stars.", (80, self.height//2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (180,180,200), 2)
                # small camera pip
                pip = cv2.resize(view, (int(self.width*0.25), int(self.height*0.25)))
                ph, pw = pip.shape[:2]
                tmp[20:20+ph, 20:20+pw] = pip
                return tmp

            # process hands
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)

            # default fingertip position center bottom
            fx, fy = self.width//2, int(self.height*0.75)
            hand_present = False

            if results.multi_hand_landmarks:
                hand_present = True
                for lm in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(view, lm, self.mp_hands.HAND_CONNECTIONS)
                lm = results.multi_hand_landmarks[0]
                fx = int(lm.landmark[8].x * self.width)
                fy = int(lm.landmark[8].y * self.height)
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
            while len(self.stars) < self.max_stars:
                self._spawn_star()

            # draw stars
            overlay = view.copy()
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
            final = cv2.addWeighted(overlay, 0.85, view, 0.15, 0)

            if self.lives <= 0:
                # Game Over
                cv2.rectangle(final, (0,0), (self.width, self.height), (10,10,10), -1)
                cv2.putText(final, f"Game Over - Score: {self.score}", (self.width//2 - 350, self.height//2), cv2.FONT_HERSHEY_DUPLEX, 2.0, (240,240,240), 3)
                self.state = 'END'

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
