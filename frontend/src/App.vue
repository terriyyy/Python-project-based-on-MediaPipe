<template>
  <!-- 路由出口：Vue 会根据网址，自动把 Home 或 GamePlay 放到这里显示 -->
  <router-view />
</template>

<style>
/* 全局样式重置 */
body {
  margin: 0;
  padding: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', sans-serif;
  background-color: #f0f2f5;
}
</style>