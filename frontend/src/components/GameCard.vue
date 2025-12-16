<template>
  <div class="card">
    <!-- 封面图区域 -->
    <div class="card-image">
      <img :src="cover" :alt="title" />
      <div class="overlay">
        <!-- 未来点击这里跳转 -->
        <button class="play-btn">立即开始</button>
      </div>
    </div>
    
    <!-- 内容区域 -->
    <div class="card-content">
      <h3 class="card-title">{{ title }}</h3>
      <p class="card-desc">{{ description }}</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GameCard',
  // 接收父组件传来的数据
  props: {
    title: String,
    description: String,
    cover: String
  }
}
</script>

<style scoped>
/* 卡片整体容器 */
.card {
  background: #ffffff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  position: relative;
  border: 1px solid #f0f0f0;
}

/* 鼠标悬停时的上浮效果 */
.card:hover {
  transform: translateY(-8px);
  box-shadow: 0 15px 30px rgba(0, 0, 0, 0.12);
}

/* 图片区域 */
.card-image {
  height: 180px;
  width: 100%;
  position: relative;
  overflow: hidden;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.card:hover .card-image img {
  transform: scale(1.05);
}

/* 悬停时的遮罩层 */
.overlay {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.card:hover .overlay {
  opacity: 1;
}

/* 按钮样式 */
.play-btn {
  padding: 10px 24px;
  background: #fff;
  color: #333;
  border: none;
  border-radius: 20px;
  font-weight: bold;
  cursor: pointer;
  transform: translateY(20px);
  transition: transform 0.3s ease;
}

.card:hover .play-btn {
  transform: translateY(0);
}

/* 文字内容区域 */
.card-content {
  padding: 20px;
  text-align: left;
}

.card-title {
  margin: 0 0 8px 0;
  font-size: 1.2rem;
  color: #2c3e50;
}

.card-desc {
  margin: 0;
  font-size: 0.9rem;
  color: #7f8c8d;
  line-height: 1.5;
  /* 限制文字只显示两行 */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>