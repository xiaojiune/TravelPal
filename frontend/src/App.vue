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
            <!-- 全局 Agent 入口：导航栏右侧按钮，点击导航栏下方浮出面板 -->
            <n-button
              class="nav-agent"
              circle
              quaternary
              :aria-label="agentOpen ? '收起 AI 助手' : '打开 AI 助手'"
              @click="agentOpen = !agentOpen"
            >
              🤖
            </n-button>
          </nav>
          <div class="app-body">
            <PendingPanel />
            <main class="main-content">
              <router-view v-slot="{ Component }">
                <keep-alive>
                  <component :is="Component" />
                </keep-alive>
              </router-view>
            </main>
          </div>
          <footer class="footer">
            <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">
              ICP备案/许可证号：桂ICP备2026015614号-1
            </a>
          </footer>
          <AgentPanel v-model:show="agentOpen" />
        </div>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
/** 根组件：全局导航栏（含 Agent 入口按钮）+ 左侧待选栏 + 页面出口 + Agent 下拉面板。导航链接覆盖 4 个页面。 */
import { ref, onMounted, onUnmounted } from 'vue'
import { zhCN, dateZhCN } from 'naive-ui'
import { themeOverrides } from '@/theme'
import PendingPanel from '@/components/PendingPanel.vue'
import AgentPanel from '@/components/AgentPanel.vue'

/** 全局 Agent 面板显隐（导航栏按钮 / 遮罩点击 / Esc 三路控制）。 */
const agentOpen = ref(false)

/** Esc 收起 Agent 面板。 */
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') agentOpen.value = false
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>
