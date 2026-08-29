<template>
  <div class="portal-page">
    <!-- 顶部极简条：品牌 + 右上登录/注册（游客态；登录态隐藏，主入口在 hero） -->
    <header class="portal-header">
      <router-link to="/" class="portal-brand">TravelPal</router-link>
      <div class="portal-header-actions">
        <template v-if="!userStore.isLoggedIn">
          <router-link to="/login" class="portal-link">登录</router-link>
          <router-link to="/register" class="portal-link portal-link-primary">注册</router-link>
        </template>
      </div>
    </header>

    <!-- Hero：品牌主张 + 主入口按钮（游客零门槛直接试用） -->
    <section class="portal-hero">
      <h1 class="hero-title">把计算交给机器，把决策留给你</h1>
      <p class="hero-sub">
        基于约束求解和大模型的旅行Agent。
      </p>
      <div class="hero-actions">
        <!-- 主入口：游客零门槛直达工作区（/home）；居中做大 -->
        <n-button type="primary" size="large" round class="hero-main-btn" @click="goWorkbench">
          开始体验
        </n-button>
      </div>
      <p class="hero-hint">已有账号？点击右上角<router-link to="/login" class="hero-hint-link">登录</router-link> / <router-link to="/register" class="hero-hint-link">注册</router-link>继续</p>
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

import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

/** 主入口：游客零门槛直达工作区（/home）；登录用户同样进入工作区。 */
function goWorkbench() {
  router.push('/home')
}
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

/* Hero */
.portal-hero {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 72px 24px;
}
.hero-title {
  font-size: 34px;
  font-weight: 700;
  line-height: 1.3;
  color: var(--tp-text);
  margin: 0 0 16px;
}
.hero-sub {
  font-size: 16px;
  line-height: 1.8;
  color: var(--tp-text-2);
  margin: 0 0 36px;
}
.hero-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}
.hero-main-btn {
  min-width: 220px;
  font-size: 18px;
  padding: 10px 0;
  font-weight: 600;
}
/* 主入口下方小字：指引右上角登录/注册 */
.hero-hint {
  margin-top: 14px;
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
}
.portal-card:hover {
  box-shadow: var(--tp-card-shadow-hover);
  transform: translateY(-2px);
}
.card-icon {
  font-size: 28px;
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
