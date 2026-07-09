<template>
  <!-- 全局导航 + 页面出口 -->
  <div id="travelpal-app">
    <nav class="nav-bar">
      <router-link to="/" class="nav-brand">TravelPal</router-link>
      <div class="nav-links">
        <router-link to="/">首页</router-link>
        <router-link to="/suggest">方案建议</router-link>
        <router-link to="/plan">规划结果</router-link>
        <router-link to="/agent">AI 助手</router-link>
        <router-link to="/history">历史记录</router-link>
      </div>
    </nav>
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
// 根组件：全局导航栏 + <router-view> 页面出口。
// 导航链接覆盖全部 5 个页面，样式内联于 <style> 中无外部依赖。
</script>
