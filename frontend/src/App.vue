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
          <!-- 工作区布局（二级界面）：完整导航 + 左侧工具轨 + Agent 助手 -->
          <template v-if="isWorkbench">
            <nav class="nav-bar">
              <div class="nav-brand-area">
                <router-link to="/" class="nav-brand">TravelPal</router-link>
              </div>
              <div class="nav-links">
                <router-link to="/home">首页</router-link>
                <router-link to="/suggest">方案建议</router-link>
                <router-link to="/plan">规划结果</router-link>
                <router-link to="/shares">分享站</router-link>
                <router-link
                  v-if="userStore.user?.role === 'super_admin'"
                  to="/admin"
                  class="nav-admin"
                >
                  管理台
                </router-link>
                <n-button size="small" secondary class="nav-reset" @click="startNewPlan">
                  🆕 新建规划
                </n-button>
              </div>
              <div class="nav-user">
                <n-dropdown
                  v-if="userStore.isLoggedIn"
                  :options="userMenuOptions"
                  @select="onUserMenu"
                >
                  <n-button text class="nav-user-trigger">
                    <span class="nav-user-name">{{ userStore.displayName }}</span>
                  </n-button>
                </n-dropdown>
                <template v-else>
                  <router-link to="/login" class="nav-login">登录</router-link>
                  <router-link to="/register" class="nav-register">注册</router-link>
                </template>
              </div>
              <!-- Agent 入口（仅二级界面）：首访自动弹 tooltip + bounce 提醒（永久一次），之后 hover 提示 -->
              <n-tooltip placement="bottom-end" :show="attention">
                <template #trigger>
                  <n-button
                    class="nav-agent"
                    :class="{ 'agent-attention': attention }"
                    secondary
                    :aria-label="agentOpen ? '收起 AI 助手' : '打开 AI 助手'"
                    @click="toggleAgent"
                  >
                    🤖 AI 助手
                  </n-button>
                </template>
                和 AI 旅行伴侣聊聊，帮你查景点、规划行程
              </n-tooltip>
            </nav>
            <div class="app-body">
              <ToolRail v-model:active="toolPanel" />
              <ToolPanel v-if="toolPanel" :active="toolPanel" />
              <main class="main-content">
                <router-view v-slot="{ Component }">
                  <keep-alive>
                    <component :is="Component" />
                  </keep-alive>
                </router-view>
              </main>
            </div>
            <AppFooter />
            <AgentPanel v-model:show="agentOpen" />
          </template>
          <!-- 门户/认证/关于 极简布局：无导航/工具轨/Agent，但保留全局备案页脚 -->
          <template v-else>
            <main class="main-content portal-main">
              <router-view v-slot="{ Component }">
                <keep-alive>
                  <component :is="Component" />
                </keep-alive>
              </router-view>
            </main>
            <AppFooter />
          </template>
        </div>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
/** 根组件：移动端降级提示 + 全局导航栏（含 Agent 入口按钮）+ 左侧工具栏/工具面板 + 页面出口 + Agent 下拉面板。 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { zhCN, dateZhCN } from 'naive-ui'
import { themeOverrides } from '@/theme'
import { usePlanStore } from '@/stores/plan'
import { useUserStore } from '@/stores/user'
import ToolRail from '@/components/ToolRail.vue'
import ToolPanel from '@/components/ToolPanel.vue'
import AgentPanel from '@/components/AgentPanel.vue'
import AppFooter from '@/components/AppFooter.vue'

const router = useRouter()
const route = useRoute()
const store = usePlanStore()
const userStore = useUserStore()

/** 是否工作区布局（二级界面）：完整导航 + 左侧工具轨 + Agent 助手。
 * 由路由 meta.useWorkbench 标记决定；门户/认证/关于走极简布局（无这些）。 */
const isWorkbench = computed(() => route.meta.useWorkbench === true)

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

/**
 * 新建规划：清空全部规划状态并回工作区首页（/home）。
 * （门户挂根路由 /，重置后应回工作区而非门户）
 */
function startNewPlan() {
  store.reset()
  router.push('/home')
}

/** 全局 Agent 面板显隐（导航栏按钮 / 遮罩点击 / Esc 三路控制）。 */
const agentOpen = ref(false)

/** 切换 AI 助手面板：打开/收起，并清除首访引导提示（undefined 恢复为 hover 提示）。 */
function toggleAgent() {
  agentOpen.value = !agentOpen.value
  attention.value = undefined
}

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

/** 用户下拉菜单项：个人中心（三级界面）+ 管理台（仅超管）+ 退出登录。 */
const userMenuOptions = computed(() => {
  const opts: { label: string; key: string }[] = [{ label: '个人中心', key: 'profile' }]
  if (userStore.user?.role === 'super_admin') {
    opts.push({ label: '管理台', key: 'admin' })
  }
  opts.push({ label: '退出登录', key: 'logout' })
  return opts
})

/** 用户下拉菜单选中：个人中心/管理台路由跳转；退出登录 → 清会话并回门户。 */
function onUserMenu(key: string | number) {
  if (key === 'profile') {
    router.push('/profile')
  } else if (key === 'admin') {
    router.push('/admin')
  } else if (key === 'logout') {
    void userStore.logout().then(() => router.push('/'))
  }
}

onMounted(() => {
  void userStore.fetchMe()
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
/* 导航用户区：未登录双链 / 已登录昵称（触发下拉菜单） */
.nav-user {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: 8px;
}
.nav-user-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nav-login,
.nav-register {
  font-size: 13px;
  color: var(--tp-text-2);
}
.nav-login:hover,
.nav-register:hover {
  color: var(--tp-primary);
}
.nav-register {
  padding-left: 12px;
  border-left: 1px solid var(--tp-border-light);
}
/* 门户/认证/关于 极简布局主区：无左侧 padding（门户全宽自绘布局）；flex:1 撑满高度，底部 AppFooter 贴底部 */
.portal-main {
  flex: 1;
  min-height: 0;
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
