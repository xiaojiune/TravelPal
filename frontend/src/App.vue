<template>
  <!-- 移动端降级提示：全屏展示，桌面端（>=768px）不渲染 -->
  <div v-if="isMobile" class="mobile-block">
    <div class="mobile-block-inner">
      <h1 class="mobile-block-title">暂只适配桌面端</h1>
      <p class="mobile-block-sub">请在电脑浏览器访问 trippal.site，体验更完整的行程规划。</p>
    </div>
  </div>
  <!-- 全局 Provider：Naive UI 中文 locale + 品牌色主题 + message/dialog（供全站替换原生 alert/confirm） -->
  <n-config-provider v-else :locale="zhCN" :date="dateZhCN" :theme-overrides="themeOverrides">
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
              <router-link to="/about" class="nav-about">关于项目 👈</router-link>
              <n-button size="small" secondary class="nav-reset" @click="startNewPlan">
                🆕 新建规划
              </n-button>
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
            <ToolRail v-model:active="toolPanel" @feedback="onFeedback" />
            <ToolPanel v-if="toolPanel" :active="toolPanel" />
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
          <FeedbackModal v-model:show="feedbackOpen" />
        </div>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
/** 根组件：移动端降级提示 + 全局导航栏（含 Agent 入口按钮）+ 左侧工具栏/工具面板 + 页面出口 + Agent 下拉面板。 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { zhCN, dateZhCN } from 'naive-ui'
import { themeOverrides } from '@/theme'
import { usePlanStore } from '@/stores/plan'
import ToolRail from '@/components/ToolRail.vue'
import ToolPanel from '@/components/ToolPanel.vue'
import AgentPanel from '@/components/AgentPanel.vue'
import FeedbackModal from '@/components/FeedbackModal.vue'

const router = useRouter()
const store = usePlanStore()

/** 移动端检测（CSS 媒体查询，含竖屏平板）；true 时整页渲染桌面端降级提示，隐藏主应用。 */
const isMobile = ref(false)
const MOBILE_QUERY = '(max-width: 767px)'
function applyIsMobile() {
  isMobile.value = window.matchMedia(MOBILE_QUERY).matches
}
let mobileQuery: MediaQueryList | undefined
onMounted(() => {
  mobileQuery = window.matchMedia(MOBILE_QUERY)
  applyIsMobile()
  mobileQuery.addEventListener('change', applyIsMobile)
})
onUnmounted(() => {
  mobileQuery?.removeEventListener('change', applyIsMobile)
})

/** 左侧工具面板当前激活项：query（查询）/ ops（操作）/ tasks（任务）；null 表示全部收起。 */
const toolPanel = ref<'query' | 'ops' | 'tasks' | null>('query')

/** 全局反馈弹窗显隐（由 ToolRail 📮 按钮触发）。 */
const feedbackOpen = ref(false)

/** ToolRail 反馈按钮事件：打开全局反馈弹窗（居中，可在任意页面）。 */
function onFeedback() {
  feedbackOpen.value = true
}

/**
 * 新建规划：清空全部规划状态并回首页（reset 补全清空待选栏/加载态/惩罚权重）。
 */
function startNewPlan() {
  store.reset()
  router.push('/')
}

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

<style scoped>
/* 移动端降级提示：全屏覆盖，品牌色背景 + 居中文案（桌面端不渲染） */
.mobile-block {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--tp-bg);
  padding: 24px;
  text-align: center;
}
.mobile-block-inner {
  max-width: 360px;
}
.mobile-block-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--tp-text);
  margin-bottom: 12px;
}
.mobile-block-sub {
  font-size: 14px;
  line-height: 1.7;
  color: var(--tp-text-2);
}
</style>
