<template>
  <!-- 全局 Provider：Naive UI 中文 locale + 品牌色主题 + message/dialog（供全站替换原生 alert/confirm） -->
  <n-config-provider :locale="zhCN" :date="dateZhCN" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <div id="travelpal-app">
          <nav class="nav-bar">
            <div class="nav-brand-area">
              <router-link to="/" class="nav-brand">TravelPal</router-link>
              <span class="nav-slogan">不占有的陪伴，不缺席的可靠</span>
            </div>
            <div class="nav-links">
              <router-link to="/">首页</router-link>
              <router-link to="/suggest">方案建议</router-link>
              <router-link to="/plan">规划结果</router-link>
              <router-link to="/history">历史记录</router-link>
            </div>
            <!-- 全局 Agent 入口：文字按钮自我解释，首访自动弹 tooltip + bounce 提醒（永久一次），之后 hover 提示 -->
            <n-tooltip placement="bottom-end" :show="attention">
              <template #trigger>
                <n-button
                  class="nav-agent"
                  :class="{ 'agent-attention': attention }"
                  secondary
                  :aria-label="agentOpen ? '收起 AI 助手' : '打开 AI 助手'"
                  @click="agentOpen = !agentOpen; attention = undefined"
                >
                  🤖 AI 助手
                </n-button>
              </template>
              和 AI 旅行伴侣聊聊，帮你查景点、规划行程
            </n-tooltip>
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

/**
 * 首访引导（永久一次，localStorage 标记）：AI 按钮自动弹 tooltip + bounce 提醒。
 * 点击按钮立即关闭；3s 后自动收起并回退为 hover 提示（undefined 恢复默认行为）。
 */
const attention = ref<boolean | undefined>(undefined)
const ATTENTION_KEY = 'travelpal_agent_attention_shown'
onMounted(() => {
  if (!localStorage.getItem(ATTENTION_KEY)) {
    localStorage.setItem(ATTENTION_KEY, '1')
    attention.value = true
    setTimeout(() => {
      attention.value = undefined
    }, 3000)
  }
})

/** Esc 收起 Agent 面板。 */
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') agentOpen.value = false
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>
