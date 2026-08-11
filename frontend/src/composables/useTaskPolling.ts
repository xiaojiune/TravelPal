/**
 * 异步任务轮询：提交后端异步规划任务后周期性查询 GET /api/tasks/{id}，
 * 直到 done/failed。
 *
 * 健壮性：
 * - 超时上限：超过 maxDurationMs（默认 5 分钟）仍无结果时 reject，避免
 *   任务永久 running 导致的无限轮询。
 * - 网络抖动跳过：单次 getTask 网络异常不立即终止，跳过本次继续轮询
 *   （直到超时或任务终态），避免偶发抖动把用户踢出。
 * - 组件卸载自动停止定时器，避免泄漏。
 */
import { onUnmounted } from 'vue'
import { getTask } from '@/services/api'

const DEFAULT_MAX_DURATION = 5 * 60 * 1000

export function useTaskPolling() {
  let timer: number | null = null

  onUnmounted(() => {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  })

  /**
   * 启动轮询，直到任务 done/failed 或超时。
   * @param taskId 后端返回的任务 UUID
   * @param interval 轮询间隔（毫秒），默认 2000
   * @param maxDuration 最大等待时长（毫秒），默认 5 分钟
   * @returns done 时返回任务的完整 result 对象
   */
  function startPolling(
    taskId: string,
    interval = 2000,
    maxDuration = DEFAULT_MAX_DURATION,
  ): Promise<Record<string, unknown>> {
    return new Promise((resolve, reject) => {
      if (timer !== null) {
        clearInterval(timer)
        timer = null
      }
      const startedAt = Date.now()
      const finish = (fn: () => void) => {
        if (timer !== null) {
          clearInterval(timer)
          timer = null
        }
        fn()
      }
      timer = window.setInterval(async () => {
        if (Date.now() - startedAt > maxDuration) {
          finish(() => reject(new Error(`规划任务超时（超过 ${maxDuration / 60000} 分钟）`)))
          return
        }
        try {
          const t = await getTask(taskId)
          if (t.status === 'done') {
            finish(() => resolve((t.result as Record<string, unknown>) || {}))
          } else if (t.status === 'failed') {
            finish(() => reject(new Error(t.error || '规划任务失败')))
          }
        } catch {
          // 网络抖动：跳过本次，下一轮继续（超时仍会兜底）
        }
      }, interval)
    })
  }

  return { startPolling }
}
