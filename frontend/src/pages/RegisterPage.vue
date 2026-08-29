<template>
  <div class="page-auth">
    <div class="auth-card">
      <h2 class="auth-title">注册</h2>
      <p class="auth-sub">创建账号，让方案分享与任务记录跟账号走</p>

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
          placeholder="至少 6 位"
          @keydown.enter="onSubmit"
        />
      </div>
      <div class="auth-field">
        <label>昵称（可选）</label>
        <n-input v-model:value="nickname" placeholder="怎么称呼你" clearable />
      </div>

      <n-button
        type="primary"
        block
        :loading="loading"
        :disabled="!email.trim() || password.length < 6"
        @click="onSubmit"
      >
        注册并登录
      </n-button>

      <p class="auth-switch">
        已有账号？
        <router-link to="/login">去登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
/** 注册页：邮箱 + 密码（≥6 位）+ 可选昵称，注册成功自动登录并跳首页。 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const message = useMessage()

const userStore = useUserStore()
const email = ref('')
const password = ref('')
const nickname = ref('')
const loading = ref(false)

/** 注册：校验必填与密码长度 → useUserStore.register（自动登录）→ 跳首页。 */
async function onSubmit() {
  if (!email.value.trim()) {
    message.warning('请输入邮箱')
    return
  }
  if (password.value.length < 6) {
    message.warning('密码至少 6 位')
    return
  }
  loading.value = true
  try {
    await userStore.register(email.value.trim(), password.value, nickname.value.trim() || undefined)
    message.success('注册成功，已自动登录')
    router.push('/home')
  } catch (e) {
    message.error(e instanceof Error ? e.message : '注册失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
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
