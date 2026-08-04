<template>
  <!-- 全局 Provider：Naive UI 中文 locale + 品牌色主题 + message/dialog（供全站替换原生 alert/confirm） -->
  <n-config-provider :locale="zhCN" :date="dateZhCN" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
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
          <footer class="footer">
            <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">
              ICP备案/许可证号：桂ICP备2026015614号-1
            </a>
          </footer>
        </div>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
/** 根组件：全局导航栏 + <router-view> 页面出口。导航链接覆盖全部 5 个页面，样式内联于 <style> 中无外部依赖。 */
import { zhCN, dateZhCN } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'

// 品牌色覆盖：对齐全站既有 #1a73e8（Google 蓝），覆盖 Naive UI 默认绿色（ADR-009 §4）
const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#1a73e8',
    primaryColorHover: '#4285f4',
    primaryColorPressed: '#1666cd',
    primaryColorSuppl: '#1a73e8',
  },
}
</script>
