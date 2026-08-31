/** 管理员操作台 API 客户端：用户 / 任务 / 反馈的只读分页列表。

  后端 require_admin 保护（admin + super_admin 均可调用）；前端界面仅 super_admin 激活，
  普通 admin 可经脚本/HTTP 调用（user-system.md 轴5）。
  */
import type { AdminFeedbackResponse, AdminTasksResponse, AdminUsersResponse } from '@/types'
import http from '@/services/http'

/** 分页列出全部用户（含 guest/user/admin/super_admin）。 */
export function getAdminUsers(page = 1, pageSize = 20): Promise<AdminUsersResponse> {
  return http.get('/admin/users', { params: { page, page_size: pageSize } })
}

/** 分页列出全部异步规划任务（suggest/plan）。 */
export function getAdminTasks(page = 1, pageSize = 20): Promise<AdminTasksResponse> {
  return http.get('/admin/tasks', { params: { page, page_size: pageSize } })
}

/** 分页列出全部用户反馈。 */
export function getAdminFeedback(page = 1, pageSize = 20): Promise<AdminFeedbackResponse> {
  return http.get('/admin/feedback', { params: { page, page_size: pageSize } })
}
