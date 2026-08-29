<template>
  <div class="portal-page">
    <!-- 顶部极简条：品牌 + 右上登录态（登录=个人信息下拉，可跳三级界面；未登录=登录/注册） -->
    <header class="portal-header">
      <router-link to="/" class="portal-brand">TravelPal</router-link>
      <div class="portal-header-actions">
        <n-dropdown
          v-if="userStore.isLoggedIn"
          :options="userMenuOptions"
          @select="onUserMenu"
        >
          <button class="portal-user-link" type="button">
            <span>{{ userStore.displayName }}</span>
            <span class="portal-user-caret">▾</span>
          </button>
        </n-dropdown>
        <template v-else>
          <router-link to="/login" class="portal-link">登录</router-link>
          <router-link to="/register" class="portal-link portal-link-primary">注册</router-link>
        </template>
      </div>
    </header>

    <!-- Hero：双栏（左文案+入口，右产品演示卡）+ 品牌渐变柔光背景 + 视差光晕 -->
    <section class="portal-hero">
      <div class="hero-bg" aria-hidden="true">
        <div class="hero-glow glow-1"></div>
        <div class="hero-glow glow-2"></div>
      </div>

      <div class="hero-left">
        <h1 class="hero-title">
          把计算交给机器，<br />
          <span class="hero-accent">把决策留给你</span>
        </h1>
        <p class="hero-sub">基于约束求解和大模型的旅行Agent，从一句话到每一程。</p>
        <div class="hero-actions">
          <n-button type="primary" size="large" round class="hero-main-btn" @click="goWorkbench">
            开始体验
          </n-button>
        </div>
        <p class="hero-trust">OR引擎 · 可编辑 · 陪伴 · 可靠</p>
        <p class="hero-hint">想留下你的痕迹？点击右上角<router-link to="/login" class="hero-hint-link">登录</router-link> / <router-link to="/register" class="hero-hint-link">注册</router-link></p>
      </div>

      <!-- 产品演示卡：mock 简化版行程表单预览（透视阴影 + 微旋转，立体真机演示感） -->
      <div class="hero-demo" aria-hidden="true">
        <div class="demo-card">
          <div class="demo-head">
            <span class="demo-title">今日行程 · 生成中</span>
            <span class="demo-badge">AI</span>
          </div>
          <div class="demo-step">
            <span class="demo-dot">1</span> 选择城市
          </div>
          <div class="demo-poi">
            <span class="poi-emoji">🏛️</span>
            <div class="poi-info">
              <span class="poi-name">故宫</span>
              <span class="poi-meta">10:00-12:00 · 建议 90 分钟</span>
            </div>
          </div>
          <div class="demo-poi">
            <span class="poi-emoji">🌿</span>
            <div class="poi-info">
              <span class="poi-name">颐和园</span>
              <span class="poi-meta">14:00-17:00 · 建议 150 分钟</span>
            </div>
          </div>
          <div class="demo-cta">🚀 生成 行程</div>
        </div>
      </div>
    </section>

    <!-- 功能入口卡：分享站 / 关于项目（仅这些留在门户） -->
    <section class="portal-cards">
      <router-link to="/shares" class="portal-card">
        <span class="card-icon">🌍</span>
        <span class="card-title">分享站</span>
        <span class="card-desc">看看大家规划的行程方案</span>
      </router-link>
      <router-link to="/about" class="portal-card">
        <span class="card-icon">ℹ️</span>
        <span class="card-title">关于项目</span>
        <span class="card-desc">项目介绍、常见问题与反馈</span>
      </router-link>
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * 品牌门户页（一级界面）：产品吸引 + 主入口 + 分享站/关于入口。
 *
 * 定位：让「首页」回归品牌呈现；真正的规划工作区在 /home（二级界面）。
 * 游客零门槛：主入口「开始体验」直达工作区（游客态）。
 * 本页为功能性骨架，视觉引导升级（hero 美化/卖点文案/动画）后续再做。
 */
defineOptions({ name: 'PortalPage' })

import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

/** 主入口：游客零门槛直达工作区（/home）；登录用户同样进入工作区。 */
function goWorkbench() {
  router.push('/home')
}

/** 门户顶部用户下拉：个人中心（三级）+ 管理台（仅超管）+ 退出登录。 */
const userMenuOptions = computed(() => {
  const opts: { label: string; key: string }[] = [{ label: '个人中心', key: 'profile' }]
  if (userStore.user?.role === 'super_admin') {
    opts.push({ label: '管理台', key: 'admin' })
  }
  opts.push({ label: '退出登录', key: 'logout' })
  return opts
})

/** 用户在门户顶部下拉选中：三级界面跳转 / 退出登录回门户。 */
function onUserMenu(key: string | number) {
  if (key === 'profile') {
    router.push('/profile')
  } else if (key === 'admin') {
    router.push('/admin')
  } else if (key === 'logout') {
    void userStore.logout().then(() => router.push('/'))
  }
}

// 门户挂载时探测登录态，确保顶部正确显示个人信息(登录)或登录/注册(未登录)
onMounted(() => {
  void userStore.fetchMe()
})
</script>

<style scoped>
.portal-page {
  /* 门户页容身在 App 的 .portal-main（flex column）内，此处撑满剩余空间，
     底部由 AppFooter 收尾（不再自立 min-height:100vh 以免挤出备案页脚）。 */
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--tp-bg);
}

/* 顶部极简条 */
.portal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: var(--tp-surface);
  border-bottom: 1px solid var(--tp-border);
}
.portal-brand {
  font-size: 22px;
  font-weight: 700;
  color: var(--tp-primary);
  text-decoration: none;
}
.portal-header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}
/* 门户顶部个人信息（登录态）：nav-link 同款框 + 下拉箭头 */
.portal-user-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--tp-border-light);
  border-radius: 8px;
  padding: 5px 12px;
  background: var(--tp-surface);
  color: var(--tp-text-2);
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.portal-user-link:hover {
  background: var(--tp-primary-soft);
  color: var(--tp-primary);
}
.portal-user-caret {
  font-size: 10px;
  color: var(--tp-text-3);
}
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

/* Hero：双栏，relative 容器承载背景/演示卡 */
.portal-hero {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 56px;
  padding: 64px 48px;
  overflow: hidden;
}
/* 背景渐变柔光 + 视差光晕（静态氛围，克制动效） */
.hero-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(120% 90% at 20% 10%, var(--tp-primary-soft) 0%, transparent 55%);
  pointer-events: none;
}
.hero-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  opacity: 0.5;
  pointer-events: none;
}
.glow-1 {
  width: 340px;
  height: 340px;
  background: var(--tp-primary-soft);
  top: -60px;
  right: 8%;
  animation: glow-drift 14s ease-in-out infinite alternate;
}
.glow-2 {
  width: 260px;
  height: 260px;
  background: var(--tp-info-soft);
  bottom: -40px;
  left: 10%;
  animation: glow-drift 18s ease-in-out infinite alternate-reverse;
}
@keyframes glow-drift {
  from {
    transform: translate(0, 0);
  }
  to {
    transform: translate(30px, -20px);
  }
}
/* 左栏：文案 + 入口 */
.hero-left {
  position: relative;
  max-width: 520px;
  animation: hero-rise 0.5s ease-out both;
}
.hero-title {
  font-size: 42px;
  font-weight: 800;
  line-height: 1.25;
  letter-spacing: -0.5px;
  color: var(--tp-text);
  margin: 0 0 20px;
}
/* 关键词品牌色强调：呼应产品哲学 */
.hero-accent {
  color: var(--tp-primary);
}
.hero-sub {
  font-size: 17px;
  line-height: 1.8;
  color: var(--tp-text-2);
  margin: 0 0 32px;
}
.hero-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}
.hero-main-btn {
  min-width: 200px;
  font-size: 17px;
  padding: 10px 0;
  font-weight: 600;
  box-shadow: 0 8px 20px rgba(32, 201, 151, 0.3);
}
/* 信任锚：入口下方卖点小字 */
.hero-trust {
  margin-top: 18px;
  font-size: 13px;
  color: var(--tp-text-3);
  letter-spacing: 0.5px;
}
/* 主入口下方小字：指引右上角登录/注册 */
.hero-hint {
  margin-top: 12px;
  font-size: 13px;
  color: var(--tp-text-3);
}
.hero-hint-link {
  color: var(--tp-primary);
  text-decoration: none;
  font-weight: 500;
}
.hero-hint-link:hover {
  text-decoration: underline;
}
/* 右栏：产品演示卡（mock 表单预览，透视阴影 + 微旋转立体感） */
.hero-demo {
  position: relative;
  flex-shrink: 0;
  animation: hero-rise 0.6s ease-out 0.12s both;
}
.demo-card {
  width: 320px;
  padding: 20px;
  border: 1px solid var(--tp-card-border);
  border-radius: 16px;
  background: var(--tp-bg-card);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.18);
  transform: rotate(2deg);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.demo-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.demo-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--tp-text);
}
.demo-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--tp-primary);
  background: var(--tp-primary-soft);
  border-radius: 6px;
  padding: 2px 8px;
}
.demo-step {
  font-size: 13px;
  color: var(--tp-text-2);
  display: flex;
  align-items: center;
  gap: 8px;
}
.demo-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--tp-primary);
  color: var(--tp-on-primary);
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.demo-poi {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border: 1px solid var(--tp-border-light);
  border-radius: 10px;
  background: var(--tp-surface);
}
.poi-emoji {
  font-size: 22px;
}
.poi-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.poi-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--tp-text);
}
.poi-meta {
  font-size: 12px;
  color: var(--tp-text-3);
}
.demo-cta {
  text-align: center;
  margin-top: 4px;
  padding: 10px;
  border-radius: 10px;
  background: var(--tp-primary);
  color: var(--tp-on-primary);
  font-size: 14px;
  font-weight: 600;
}
/* 首屏入场微动效：文案/演示卡依次淡入上移 */
@keyframes hero-rise {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}


/* 功能入口卡 */
.portal-cards {
  display: flex;
  justify-content: center;
  gap: 20px;
  padding: 0 24px 56px;
  flex-wrap: wrap;
}
.portal-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 240px;
  padding: 24px 16px;
  border: 1px solid var(--tp-card-border);
  border-radius: 12px;
  background: var(--tp-bg-card);
  text-decoration: none;
  box-shadow: var(--tp-card-shadow);
  transition: box-shadow 0.2s, transform 0.2s;
  position: relative;
  overflow: hidden;
}
/* 顶部品牌色条：hover 时展开 */
.portal-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--tp-primary);
  opacity: 0;
  transition: opacity 0.2s;
}
.portal-card:hover::before {
  opacity: 1;
}
.portal-card:hover {
  box-shadow: var(--tp-card-shadow-hover);
  transform: translateY(-2px);
}
/* 图标圆形底：提升入口识别度 */
.card-icon {
  font-size: 24px;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--tp-primary-soft);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 6px;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--tp-text);
}
.card-desc {
  font-size: 13px;
  color: var(--tp-text-2);
  text-align: center;
}
</style>
