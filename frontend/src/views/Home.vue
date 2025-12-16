<template>
  <div class="home-container">
    
    <!-- 1. 顶部 Hero 区域 -->
    <header class="hero-section">
      <div class="hero-content">
        <h1 class="main-title">Mini Game Hub</h1>
        <p class="sub-title">A MediaPipe-Driven Vision Interaction Playground</p>
      </div>
      <div class="wave"></div>
    </header>

    <!-- 2. 中部核心内容 -->
    <main class="content-wrapper">
      <div class="section-header">
        <h2>Interactive Experiment Showcase</h2>
        <span class="badge">More</span>
      </div>

      <!-- ============================================== -->
      <!-- [修改点 1] 这里的 v-for 循环改成了 games -->
      <!-- [修改点 2] 增加了 @click 点击事件 -->
      <!-- ============================================== -->
      <div class="games-grid">
        <GameCard 
          v-for="game in games" 
          :key="game.id"
          :title="game.title"
          :description="game.description" 
          :cover="game.cover"
          @click="goToGame(game.id)" 
        />
        <!-- 注意：后端 info.json 里的字段是 description，所以上面 props 要改对 -->
      </div>
      
    </main>

    <!-- 3. 底部信息 -->
    <footer class="footer">
      <p>© 2025 Python小组作业项目展示</p>
      <p style="font-size: 0.8rem; opacity: 0.7;">Designed by Frontend Team</p>
    </footer>

  </div>
</template>

<script>
import GameCard from '@/components/GameCard.vue'
// [修改点 3] 引入 API
import { api } from '@/api/index'

export default {
  name: 'HomeView',
  components: {
    GameCard
  },
  data() {
    return {
      // 这里的 mockGames 被删除了，换成空的 games 数组等待接收数据
      games: []
    }
  },
  // [修改点 4] 页面加载时自动请求后端
  mounted() {
    this.loadGames()
  },
  methods: {
    // 获取游戏列表
    async loadGames() {
      try {
        const res = await api.getData()
        console.log("后端返回的数据:", res.data)
        // 赋值给页面变量
        if(res.data.code === 200) {
          this.games = res.data.data
        }
      } catch (error) {
        console.error("无法连接后端，请确认 python main.py 已启动", error)
      }
    },
    // [修改点 5] 跳转逻辑
    goToGame(id) {
      console.log("准备跳转到游戏:", id)
      // 使用路由跳转到 /game/xxx
      this.$router.push(`/game/${id}`)
    }
  }
}
</script>

<style scoped>
/* 样式保持你原来的不变，非常完美 */
.home-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f8f9fa;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.hero-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 80px 20px;
  text-align: center;
  margin-bottom: 40px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.main-title {
  font-size: 3rem;
  margin: 0;
  letter-spacing: 2px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.sub-title {
  font-size: 1.2rem;
  opacity: 0.9;
  margin-top: 10px;
  font-weight: 300;
}

.content-wrapper {
  flex: 1; 
  max-width: 1200px;
  width: 90%;
  margin: 0 auto;
  padding-bottom: 60px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding: 0 10px;
}

.section-header h2 {
  font-size: 1.8rem;
  color: #333;
  position: relative;
  padding-left: 15px;
}
.section-header h2::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 5px;
  height: 24px;
  background: #764ba2;
  border-radius: 3px;
}

.badge {
  background: #eef2ff;
  color: #667eea;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: bold;
}

.games-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 30px;
}

/* Footer 样式 */
.footer {
  text-align: center;
  padding: 30px;
  background: #2d3436;
  color: #b2bec3;
  margin-top: auto;
}
</style>