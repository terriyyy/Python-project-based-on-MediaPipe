
import { createRouter, createWebHistory } from 'vue-router'
// 引入组件
import Home from '@/views/Home.vue'
// 2. 引入游戏播放页 
import GamePlay from '@/views/GamePlay.vue' 

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    // 动态路由：:id 会自动匹配你点的游戏名字
    path: '/game/:id',
    name: 'GamePlay',
    component: GamePlay
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router