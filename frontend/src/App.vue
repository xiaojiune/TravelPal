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
          <!-- 全局 Agent 入口：右下角浮动按钮唤起右侧抽屉，跨页面常驻 -->
          <n-button class="agent-fab" circle size="large" @click="agentOpen = !agentOpen">
            🤖
          </n-button>
          <AgentDrawer v-model:show="agentOpen" />
        </div>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
/** 根组件：全局导航栏 + <router-view> 页面出口 + 全局 Agent 抽屉入口。导航链接覆盖 4 个页面，样式内联于 <style> 中无外部依赖。 */
import { ref } from 'vue'
import { zhCN, dateZhCN } from 'naive-ui'
import { themeOverrides } from '@/theme'
import AgentDrawer from '@/components/AgentDrawer.vue'

/** 全局 Agent 抽屉显隐。 */
const agentOpen = ref(false)
</script>
