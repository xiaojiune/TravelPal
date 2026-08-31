/** 用户全局状态：登录态加载、登录/注册/登出。Pinia setup 语法。

  登录态由后端 httpOnly Cookie 提供服务端会话；本 store 仅在前端维护
  「当前是否已登录」的镜像（user）。刷新页面后 Cookie 仍在，靠 fetchMe()
  恢复登录态；未登录（401）则视为空，不阻断导航（访客零门槛）。
  */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getAuthMe, postAuthLogin, postAuthLogout, postAuthRegister } from '@/services/auth'
import { usePlanStore } from '@/stores/plan'
import type { UserOut } from '@/types'

export const useUserStore = defineStore('user', () => {
  /** 当前登录用户；null 表示未登录。 */
  const user = ref<UserOut | null>(null)
  /** 是否已尝试恢复登录态（避免重复 fetchMe）。 */
  const ready = ref(false)

  /** 是否已登录（后端会话有效）。 */
  const isLoggedIn = computed(() => user.value !== null)

  /** 导航栏展示名：优先昵称，次为邮箱，否则占位。 */
  const displayName = computed(() => user.value?.nickname || user.value?.email || '未登录')

  /** 从后端恢复登录态（GET /me）；401 视为未登录，不抛错。 */
  async function fetchMe() {
    try {
      user.value = await getAuthMe()
    } catch {
      user.value = null
    } finally {
      ready.value = true
    }
  }

  /**
   * 登录：校验凭据并写入 user；失败抛错（错误提示由调用方展示）。
   * @param email - 登录邮箱
   * @param password - 密码
   */
  async function login(email: string, password: string) {
    user.value = await postAuthLogin({ email, password })
    // 登录切换身份：清空当前（游客/上一位）界面数据，进入本用户干净工作区
    usePlanStore().reset()
  }

  /**
   * 注册并自动登录。
   * @param email - 注册邮箱
   * @param password - 密码（≥6 位）
   * @param nickname - 昵称（可选）
   */
  async function register(email: string, password: string, nickname?: string) {
    user.value = await postAuthRegister({ email, password, nickname })
    // 新账号注册：默认干净工作区
    usePlanStore().reset()
  }

  /** 登出：清后端会话 + 本地 user + 覆盖所有界面数据（每个身份有自己干净界面）。 */
  async function logout() {
    try {
      await postAuthLogout()
    } finally {
      user.value = null
      // 登出即"遗忘"：清空全部规划/对话数据，回到游客干净界面（游客数据不保存）
      usePlanStore().reset()
    }
  }

  return { user, ready, isLoggedIn, displayName, fetchMe, login, register, logout }
})
