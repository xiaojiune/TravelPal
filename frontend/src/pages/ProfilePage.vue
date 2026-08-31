<template>
  <div class="page-profile">
    <div class="profile-header">
      <span class="profile-avatar">{{ avatarText }}</span>
      <div class="profile-meta">
        <h2 class="profile-name">{{ userStore.displayName }}</h2>
        <p class="profile-email">{{ userStore.user?.email }}</p>
      </div>
    </div>

    <div class="profile-info">
      <div class="info-row">
        <span class="info-label">角色</span>
        <span class="info-value">{{ roleLabel }}</span>
      </div>
    </div>

    <!-- 占位：个人中心界面（当前仅标识，功能后续扩展） -->
    <div class="profile-placeholder">
      <span>个人中心</span>
      <p>这里将展示你的历史方案、收藏与偏好设置。（占位，待扩展）</p>
    </div>

    <div class="profile-actions">
      <n-button type="primary" @click="router.push('/home')">返回工作区</n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
/** 个人中心页（三级界面）：点击右上角头像进入。当前为占位——展示身份信息，功能待扩展。 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

defineOptions({ name: 'ProfilePage' })

const router = useRouter()
const userStore = useUserStore()

/** 头像首字符（昵称或邮箱首字母）。 */
const avatarText = computed(() => {
  const n = (userStore.displayName ?? '').trim()
  return n.charAt(0).toUpperCase() || '?'
})

/** 角色中文标签（user/admin/super_admin）。 */
const roleLabel = computed(() => {
  const role = userStore.user?.role
  if (role === 'super_admin') return '超级管理员'
  if (role === 'admin') return '管理员'
  return '普通用户'
})
</script>

<style scoped>
.page-profile {
  max-width: 640px;
  /* 水平居中 */
  margin: 0 auto;
  padding: 0 16px;
}
.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.profile-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--tp-primary-soft);
  color: var(--tp-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  flex-shrink: 0;
}
.profile-meta h2 {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 600;
  color: var(--tp-text);
}
.profile-email {
  margin: 0;
  font-size: 13px;
  color: var(--tp-text-3);
}
.profile-info {
  margin-bottom: 24px;
  padding: 16px;
  border: 1px solid var(--tp-card-border);
  border-radius: 8px;
  background: var(--tp-bg-card);
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.info-label {
  font-size: 13px;
  color: var(--tp-text-2);
}
.info-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--tp-text);
}
.profile-placeholder {
  padding: 24px;
  border: 1px dashed var(--tp-border);
  border-radius: 8px;
  text-align: center;
  color: var(--tp-text-3);
}
.profile-placeholder span {
  font-size: 14px;
  font-weight: 600;
  color: var(--tp-text-2);
}
.profile-placeholder p {
  margin: 8px 0 0;
  font-size: 13px;
}
.profile-actions {
  margin-top: 24px;
}
</style>
