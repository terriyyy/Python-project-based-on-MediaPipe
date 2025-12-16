<template>
  <div class="game-play-container">
    <div class="header">
      <button @click="$router.push('/')">← 返回首页</button>
      <h2>正在运行: {{ gameId }}</h2>
    </div>

    <!-- 核心：视频流显示区域 -->
    <div class="video-wrapper">
      <!-- 直接把 img 的 src 指向后端的流接口 -->
      <img 
        :src="streamUrl" 
        alt="游戏画面加载中..." 
        class="live-stream"
      />
    </div>

    <div class="instructions">
      <p>请确保后端服务已启动，并且没有其他程序占用摄像头。</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GamePlay',
  data() {
    return {
      gameId: '',
      streamUrl: ''
    }
  },
  mounted() {
    // 从路由参数里获取 gameId (比如 snake, hand)
    this.gameId = this.$route.params.id
    // 拼接后端视频流地址
    this.streamUrl = `http://localhost:8000/api/stream/${this.gameId}`
  }
}
</script>

<style scoped>
.game-play-container {
  text-align: center;
  padding: 20px;
  background: #2c3e50;
  min-height: 100vh;
  color: white;
}
.video-wrapper {
  margin: 30px auto;
  border: 5px solid #fff;
  border-radius: 10px;
  display: inline-block;
  overflow: hidden;
  box-shadow: 0 0 20px rgba(0,0,0,0.5);
}
.live-stream {
  display: block;
  max-width: 100%;
  height: auto; 
}
</style>