/**
 * 异步任务轮询：提交后端异步规划任务后周期性查询 GET /api/tasks/{id}，
 * 直到 done/failed。组件卸载时自动停止，避免定时器泄漏。
 */
import { onUnmounted } from 'vue'
import { getTask } from '@/services/api'

export function useTaskPolling() {
  let timer: number | null = null

  onUnmounted(() => {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  })

  /**
   * 启动轮询，直到任务 done/failed。
   * @param taskId 后端返回的任务 UUID
   * @param interval 轮询间隔（毫秒），默认 2000
   * @returns done 时返回任务的完整 result 对象
   */
  function startPolling(taskId: string, interval = 2000): Promise<Record<string, unknown>> {
    return new Promise((resolve, reject) => {
      if (timer !== null) {
        clearInterval(timer)
        timer = null
      }
      timer = window.setInterval(async () => {
        try {
          const t = await getTask(taskId)
          if (t.status === 'done') {
            if (timer !== null) { clearInterval(timer); timer = null }
            resolve((t.result as Record<string, unknown>) || {})
          } else if (t.status === 'failed') {
            if (timer !== null) { clearInterval(timer); timer = null }
            reject(new Error(t.error || '规划任务失败'))
          }
        } catch (e) {
          if (timer !== null) { clearInterval(timer); timer = null }
          reject(e)
        }
      }, interval)
    })
  }

  return { startPolling }
}
