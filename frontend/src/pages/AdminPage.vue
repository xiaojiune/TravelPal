<template>
  <div class="page-admin">
    <div class="admin-header">
      <h2>管理台</h2>
      <n-button size="small" strong @click="openMonitor">监控看板</n-button>
    </div>
    <p class="subtitle">用户 / 任务 / 反馈（只读，仅超级管理员可见）</p>

    <n-tabs v-model:value="tab" type="line" animated>
      <n-tab-pane name="users" tab="用户">
        <n-data-table
          :columns="userColumns"
          :data="users"
          :pagination="usersPagination"
          :bordered="false"
        />
      </n-tab-pane>
      <n-tab-pane name="tasks" tab="任务">
        <n-data-table
          :columns="taskColumns"
          :data="tasks"
          :pagination="tasksPagination"
          :bordered="false"
        />
      </n-tab-pane>
      <n-tab-pane name="feedback" tab="反馈">
        <n-data-table
          :columns="feedbackColumns"
          :data="feedbacks"
          :pagination="feedbackPagination"
          :bordered="false"
        />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
/**
 * 管理台页：用户 / 任务 / 反馈的分页只读列表（轴5）。
 * 仅 super_admin 可进入（路由守卫 requiresAdmin 控制）；后端 require_admin 放行 admin+super_admin。
 * 普通 admin 后端可调 API（脚本/HTTP），前端界面暂不激活入口。
 */
import { ref, computed, watch, onMounted } from 'vue'
import { h } from 'vue'
import { NButton, NTag } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { getAdminFeedback, getAdminTasks, getAdminUsers } from '@/services/admin'
import type { AdminFeedback, AdminTask, AdminUser } from '@/types'

// ====== 页面状态 ======
const tab = ref<'users' | 'tasks' | 'feedback'>('users')
const PAGE_SIZE = 20

const users = ref<AdminUser[]>([])
const totalUsers = ref(0)
const usersPage = ref(1)
const tasks = ref<AdminTask[]>([])
const totalTasks = ref(0)
const tasksPage = ref(1)
const feedbacks = ref<AdminFeedback[]>([])
const totalFeedback = ref(0)
const feedbackPage = ref(1)

// ====== 角色/状态文案映射 ======
const roleText: Record<string, string> = {
  super_admin: '超级管理员',
  admin: '普通管理员',
  user: '普通用户',
  guest: '访客',
}

function formatTime(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleString()
}

// 跳转到监控看板（Grafana，经 nginx /grafana/ 子路径反代，需登录）
function openMonitor() {
  window.open('/grafana/', '_blank', 'noopener')
}

// ====== 表格列定义 ======
const userColumns: DataTableColumns<AdminUser> = [
  {
    title: '角色',
    key: 'role',
    render: (row) =>
      h(
        NTag,
        {
          size: 'small',
          type: row.role === 'super_admin' ? 'warning' : 'default',
          bordered: false,
        },
        { default: () => roleText[row.role] ?? row.role },
      ),
  },
  { title: '邮箱', key: 'email', render: (row) => row.email ?? '-' },
  { title: '昵称', key: 'nickname', render: (row) => row.nickname ?? '-' },
  { title: '激活', key: 'is_active', render: (row) => (row.is_active ? '是' : '否') },
  { title: '创建时间', key: 'created_at', render: (row) => formatTime(row.created_at) },
]

const taskColumns: DataTableColumns<AdminTask> = [
  { title: '类型', key: 'task_type', width: 110 },
  { title: '状态', key: 'status' },
  { title: '创建时间', key: 'created_at', render: (row) => formatTime(row.created_at) },
  {
    title: '结束时间',
    key: 'finished_at',
    render: (row) => (row.finished_at ? formatTime(row.finished_at) : '-'),
  },
]

const feedbackColumns: DataTableColumns<AdminFeedback> = [
  { title: '内容', key: 'content', width: 260, ellipsis: true },
  { title: '名称', key: 'name', render: (row) => row.name ?? '-' },
  { title: '联系方式', key: 'contact', render: (row) => row.contact ?? '-' },
  { title: '评分', key: 'rating', render: (row) => row.rating ?? '-' },
  { title: '页面', key: 'page', render: (row) => row.page ?? '-' },
  { title: '时间', key: 'created_at', render: (row) => formatTime(row.created_at) },
]

// ====== 分页配置（响应式，onUpdatePage 触发重新加载） ======
const usersPagination = computed(() => ({
  page: usersPage.value,
  pageSize: PAGE_SIZE,
  itemCount: totalUsers.value,
  pageCount: Math.ceil(totalUsers.value / PAGE_SIZE) || 1,
  showSizePicker: false,
  onUpdatePage: (p: number) => {
    usersPage.value = p
    void loadUsers()
  },
}))

const tasksPagination = computed(() => ({
  page: tasksPage.value,
  pageSize: PAGE_SIZE,
  itemCount: totalTasks.value,
  pageCount: Math.ceil(totalTasks.value / PAGE_SIZE) || 1,
  showSizePicker: false,
  onUpdatePage: (p: number) => {
    tasksPage.value = p
    void loadTasks()
  },
}))

const feedbackPagination = computed(() => ({
  page: feedbackPage.value,
  pageSize: PAGE_SIZE,
  itemCount: totalFeedback.value,
  pageCount: Math.ceil(totalFeedback.value / PAGE_SIZE) || 1,
  showSizePicker: false,
  onUpdatePage: (p: number) => {
    feedbackPage.value = p
    void loadFeedback()
  },
}))

// ====== 数据加载 ======
async function loadUsers() {
  try {
    const res = await getAdminUsers(usersPage.value, PAGE_SIZE)
    users.value = res.items
    totalUsers.value = res.total
  } catch {
    users.value = []
  }
}

async function loadTasks() {
  try {
    const res = await getAdminTasks(tasksPage.value, PAGE_SIZE)
    tasks.value = res.items
    totalTasks.value = res.total
  } catch {
    tasks.value = []
  }
}

async function loadFeedback() {
  try {
    const res = await getAdminFeedback(feedbackPage.value, PAGE_SIZE)
    feedbacks.value = res.items
    totalFeedback.value = res.total
  } catch {
    feedbacks.value = []
  }
}

// ====== 切换 tab 时加载对应列表 ======
watch(tab, (t) => {
  if (t === 'users') void loadUsers()
  else if (t === 'tasks') void loadTasks()
  else void loadFeedback()
})

onMounted(() => {
  void loadUsers()
})
</script>

<style scoped>
.page-admin {
  max-width: 960px;
  /* 水平居中 */
  margin: 0 auto;
  padding: 0 16px;
}
.page-admin h2 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
  color: var(--tp-text);
}
.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.page-admin .subtitle {
  margin: 0 0 20px;
  font-size: 13px;
  color: var(--tp-text-2);
}
</style>
