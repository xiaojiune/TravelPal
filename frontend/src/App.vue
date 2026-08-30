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
              <!-- 返回门户（非门户页）：Logo 左侧轻量链接 -->
              <router-link to="/" class="nav-portal-link">⌂ 门户</router-link>
              <div class="nav-brand-area">
                <router-link to="/home" class="nav-brand">TravelPal</router-link>
              </div>
              <div class="nav-links">
                <router-link to="/home">首页</router-link>
                <router-link to="/or">方案建议</router-link>
                <router-link to="/show">规划结果</router-link>
                <router-link to="/shares">分享站</router-link>
              </div>
              <div class="nav-user">
                <!-- 个人信息（导航最右）：nav-link 同款框，完整显示昵称/邮箱 -->
                <n-dropdown
                  v-if="userStore.isLoggedIn"
                  :options="userMenuOptions"
                  @select="onUserMenu"
                >
                  <button class="nav-user-link" type="button">
                    <span class="nav-user-name">{{ userStore.displayName }}</span>
                    <span class="nav-user-caret">▾</span>
                  </button>
                </n-dropdown>
                <template v-else>
                  <router-link to="/login" class="portal-link">登录</router-link>
                  <router-link to="/register" class="portal-link portal-link-primary">注册</router-link>
                </template>
              </div>
            </nav>
            <div class="app-body">
              <ToolRail v-model:active="toolPanel" />
              <!-- 工具面板：展开/收起的左侧滑入滑出动效（与右侧 Agent 栏呼应） -->
              <Transition name="tool-slide">
                <ToolPanel v-if="toolPanel" :active="toolPanel" />
              </Transition>
              <main class="main-content">
                <!-- 内容滚动区：右上 AI 助手 + 页面出口 -->
                <div class="content-scroll">
                  <!-- 右上角 AI 助手（wrapper absolute，不占文档流、不推低内容） -->
                  <div class="content-float">
                    <n-tooltip placement="bottom-end" :show="attention">
                      <template #trigger>
                        <button
                          class="agent-round"
                          :class="{ 'agent-attention': attention }"
                          :aria-label="agentOpen ? '收起 AI 助手' : '打开 AI 助手'"
                          @click="toggleAgent"
                        >
                          🤖
                        </button>
                      </template>
                      和 AI 旅行伴侣聊聊，帮你查景点、规划行程
                    </n-tooltip>
                  </div>
                  <router-view v-slot="{ Component }">
                    <keep-alive>
                      <component :is="Component" />
                    </keep-alive>
                  </router-view>
                </div>
                <!-- 备案页脚：挂载主内容区（随 Agent 右栏让宽），非全局整体 -->
                <AppFooter />
              </main>
              <!-- 右侧共创栏（Agent 固定右栏）：与主内容并排 flex 行，展开时主内容让宽度 -->
              <AgentPanel v-model:show="agentOpen" />
            </div>
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
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
  // 仅在需要登录态的工作区布局探测用户（门户/认证/关于为公开页，不触发 /me，
  // 避免未登录时后端 401 日志噪音）；守卫路由（/profile /admin）内部仍会按需 fetchMe。
  if (isWorkbench.value) {
    void userStore.fetchMe()
  }
})

// 异步任务集合生命周期：登录→持久化 + 从 localStorage 唤回；登出/切游客→清空。
// 与"主动退出删除、关闭/强制刷新浏览器保留"一致（退出触发 isLoggedIn=false → 清空）。
watch(
  () => userStore.isLoggedIn,
  (loggedIn) => {
    if (loggedIn) {
      store.setPersistTasks(true)
      store.hydrateTasks()
    } else {
      store.setPersistTasks(false) // 内部清空内存 + localStorage + 停轮询
    }
  },
)

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
/* 返回门户（非门户页）：Logo 左侧，靛蓝色 outline 按钮（显眼） */
.nav-portal-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  color: var(--tp-info);
  text-decoration: none;
  padding: 5px 12px;
  border: 1px solid var(--tp-info);
  border-radius: 8px;
  background: var(--tp-surface);
  transition: background 0.2s, color 0.2s;
}
.nav-portal-link:hover {
  background: var(--tp-info);
  color: var(--tp-on-primary);
}
/* 导航用户区：未登录双链 / 已登录个人信息框（触发下拉菜单）；推至最右 */
.nav-user {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}.nav-user-name {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 个人信息：nav-link 同款框样式（完整显示昵称/邮箱，不截断） */
.nav-user-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--tp-border-light);
  border-radius: 8px;
  padding: 4px 12px;
  background: var(--tp-surface);
  color: var(--tp-text-2);
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.nav-user-link:hover {
  background: var(--tp-primary-soft);
  color: var(--tp-primary);
}
.nav-user-caret {
  font-size: 10px;
  color: var(--tp-text-3);
}
/* 登录/注册（未登录态）：复用门户页 portal-link 样式 */
.portal-link {
  font-size: 14px;
  color: var(--tp-text-2);
  text-decoration: none;
  padding: 6px 12px;
  border-radius: 6px;
}
.portal-link:hover {
  color: var(--tp-primary);
  background: var(--tp-primary-soft);
}
.portal-link-primary {
  color: var(--tp-primary);
  font-weight: 600;
  border: 1px solid var(--tp-primary);
}
/* 内容区右上浮动工具栏（wrapper）：absolute 浮于内容区上方，不占文档流、不推低内容 */
.content-float {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 12px;
}
/* AI 助手圆形按钮：实心品牌色底 + 投影，更醒目 */
.agent-round {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background: var(--tp-primary);
  font-size: 22px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 8px var(--tp-primary);
  transition: transform 0.2s, box-shadow 0.2s;
}
.agent-round:hover {
  background: var(--tp-primary-hover);
  transform: scale(1.08);
  box-shadow: 0 4px 12px var(--tp-primary);
}
/* 门户/认证/关于 极简布局主区：无左侧 padding（门户全宽自绘布局）；flex:1 撑满高度，底部 AppFooter 贴底部 */
.portal-main {
  flex: 1;
  min-height: 0;
  padding: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
</style>
