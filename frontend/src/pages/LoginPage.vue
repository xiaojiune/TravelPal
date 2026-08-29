<template>
  <div class="auth-page">
    <!-- 顶部品牌条：左 Logo(回门户) + 右 返回门户按钮 -->
    <header class="auth-header">
      <router-link to="/" class="auth-brand">TravelPal</router-link>
      <router-link to="/" class="auth-back">← 返回门户</router-link>
    </header>

    <div class="page-auth">
      <div class="auth-card">
        <h2 class="auth-title">登录</h2>
        <p class="auth-sub">登录后可关联你的方案分享与任务记录</p>

        <div class="auth-field">
          <label>邮箱</label>
          <n-input v-model:value="email" placeholder="请输入邮箱" clearable />
        </div>
        <div class="auth-field">
          <label>密码</label>
          <n-input
            v-model:value="password"
            type="password"
            show-password-on="click"
            placeholder="请输入密码"
            @keydown.enter="onSubmit"
          />
        </div>

        <n-button
          type="primary"
          block
          :loading="loading"
          :disabled="!email.trim() || !password"
          @click="onSubmit"
        >
          登录
        </n-button>

        <p class="auth-switch">
          还没有账号？
          <router-link to="/register">去注册</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/** 登录页：邮箱 + 密码，成功写入 user store 并按 redirect 或首页跳转。 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const message = useMessage()

const userStore = useUserStore()
const email = ref('')
const password = ref('')
const loading = ref(false)

/** 登录：非空校验 → useUserStore.login → 成功后按 redirect(若为站内路径) 或首页跳转。 */
async function onSubmit() {
  if (!email.value.trim() || !password.value) {
    message.warning('请输入邮箱和密码')
    return
  }
  loading.value = true
  try {
    await userStore.login(email.value.trim(), password.value)
    message.success('登录成功')
    // redirect 仅接受站内路径，防止开放重定向；无 redirect 时默认落工作区 /home
    const redirect =
      typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
        ? route.query.redirect
        : '/home'
    router.push(redirect)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 外层：全高纵向布局，header 置顶、表单区居中 */
.auth-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--tp-bg);
}
/* 顶部品牌条：左 Logo(回门户) + 右 返回门户 */
.auth-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: var(--tp-surface);
  border-bottom: 1px solid var(--tp-border);
}
.auth-brand {
  font-size: 22px;
  font-weight: 700;
  color: var(--tp-primary);
  text-decoration: none;
}
/* 返回门户：靛蓝 outline 按钮（与门户/About 一致） */
.auth-back {
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
.auth-back:hover {
  background: var(--tp-info);
  color: var(--tp-on-primary);
}
.page-auth {
  display: flex;
  justify-content: center;
  padding: 48px 16px 0;
}
.auth-card {
  width: 100%;
  max-width: 360px;
  padding: 28px;
  border: 1px solid var(--tp-border);
  border-radius: 12px;
  background: var(--tp-surface);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}
.auth-title {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 600;
  color: var(--tp-text);
}
.auth-sub {
  margin: 0 0 20px;
  font-size: 13px;
  color: var(--tp-text-2);
}
.auth-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}
.auth-field label {
  font-size: 13px;
  color: var(--tp-text-2);
}
.auth-switch {
  margin: 16px 0 0;
  text-align: center;
  font-size: 13px;
  color: var(--tp-text-2);
}
.auth-switch a {
  color: var(--tp-primary);
}
</style>
