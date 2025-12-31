# games/parkour_game/src/parkour_core.py
import time
import random
import math

class Obstacle:
    def __init__(self, lane, obs_type, z_pos=0.0):
        self.lane = lane      # -1: Left, 0: Mid, 1: Right
        self.type = obs_type  # JUMP, HURDLE, TUNNEL, FULL
        self.z = z_pos        # 0.0 (Far) -> 1.0 (Near)
        self.passed = False

class ParkourCore:
    def __init__(self):
        # 游戏状态
        self.state = "SELECT_TIME" 
        self.target_time = 60       
        self.start_time = 0
        self.elapsed_time = 0
        self.death_time = 0 
        
        # 玩家属性
        self.lane = 0        
        self.action_state = "RUN" 
        self.action_timer = 0     
        self.jump_duration = 0.6  
        self.slide_duration = 0.8 
        
        # 场景控制
        self.obstacles = []
        self.base_speed = 0.006   
        self.spawn_timer = 0
        
        # 速度倍率 (用于渲染同步)
        self.current_speed_factor = 1.0

    def start_game(self, duration):
        self.target_time = duration
        self.state = "PLAYING"
        self.start_time = time.time()
        self.obstacles = []
        self.lane = 0
        self.base_speed = 0.006
        self.action_state = "RUN"
        self.spawn_timer = 0

    def update(self, trigger_action=None):
        """核心逻辑更新帧"""
        if self.state != "PLAYING": return

        current_t = time.time()
        self.elapsed_time = current_t - self.start_time

        # 胜利检测
        if self.elapsed_time >= self.target_time:
            self.state = "VICTORY"
            self.death_time = current_t
            return

        # 1. 玩家控制处理
        if trigger_action == "LEFT" and self.lane > -1:
            self.lane -= 1
        elif trigger_action == "RIGHT" and self.lane < 1:
            self.lane += 1
        elif trigger_action == "UP" and self.action_state == "RUN":
            self.action_state = "JUMP"
            self.action_timer = current_t
        elif trigger_action == "DOWN" and self.action_state == "RUN":
            self.action_state = "SLIDE"
            self.action_timer = current_t

        # 2. 速度计算 (随时间越来越快)
        speed_boost = math.log(1 + self.elapsed_time / 45.0) * 0.3
        self.current_speed_factor = 1 + min(1.5, speed_boost)
        current_speed = self.base_speed * self.current_speed_factor

        # 3. 动作状态恢复
        if self.action_state == "JUMP":
            if current_t - self.action_timer > self.jump_duration: self.action_state = "RUN"
        elif self.action_state == "SLIDE":
            if current_t - self.action_timer > self.slide_duration: self.action_state = "RUN"

        # 4. 障碍物生成逻辑
        self.spawn_timer += 1
        spawn_interval = max(35, int(80 - self.elapsed_time * 0.4))
        
        if self.spawn_timer > spawn_interval:
            self.obstacles.extend(self._generate_wave())
            self.spawn_timer = 0

        # 5. 障碍物移动与碰撞
        for i in range(len(self.obstacles) - 1, -1, -1):
            obs = self.obstacles[i]
            # 透视加速效果
            perspective_boost = 1.0 + (obs.z * 2.5) 
            obs.z += current_speed * perspective_boost

            if obs.z > 1.3: 
                self.obstacles.pop(i)
                continue

            # 碰撞判定区域 (0.85 - 1.0)
            if 0.85 < obs.z < 1.0 and not obs.passed:
                if obs.lane == self.lane:
                    collision = False
                    if obs.type == "FULL": collision = True 
                    elif obs.type == "JUMP" and self.action_state != "JUMP": collision = True
                    elif obs.type == "TUNNEL" and self.action_state != "SLIDE": collision = True
                    elif obs.type == "HURDLE" and self.action_state == "RUN": collision = True
                    
                    if collision:
                        self.state = "GAME_OVER"
                        self.death_time = time.time()
                    else:
                        obs.passed = True 

    def _generate_wave(self):
        """生成一波障碍物"""
        t = self.elapsed_time
        probs = [1.0, 0.0, 0.0] 
        if t < 20: probs = [1.0, 0.0, 0.0] 
        elif t < 40: probs = [0.8, 0.2, 0.0] 
        elif t < 80: probs = [0.5, 0.5, 0.0] 
        else: probs = [0.1, 0.5, 0.4] 
            
        mode = random.choices([1, 2, 3], weights=probs, k=1)[0]
        lanes = [-1, 0, 1]
        
        if mode == 1: selected = [random.choice(lanes)]
        elif mode == 2: selected = random.sample(lanes, 2)
        else: selected = lanes

        types = ["JUMP", "HURDLE", "TUNNEL", "FULL"]
        wave = []
        gen_types = []
        
        for l in selected:
            t = random.choice(types)
            gen_types.append(t)
            wave.append(Obstacle(l, t, 0.0))
            
        # 避免三路全是红墙必死
        if mode == 3 and gen_types.count("FULL") == 3:
            wave[1].type = "JUMP" # 强行改中间为可跳跃
            
        return wave