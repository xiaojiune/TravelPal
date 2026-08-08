/** HTTP 客户端：统一 axios 实例 + 响应错误规范化。

 统一处理三件事：
 - baseURL /api + 30s 超时
 - response 拦截器直接返回 r.data（调用方不再重复 .then(r => r.data)）
 - error 拦截器把后端错误提取为统一 Error 消息（FastAPI detail：
   422 校验失败为数组逐项 msg 拼接；其余取 detail 或 axios 错误 message）

 调用方只需 catch 后用 e.message 展示，所有错误形态统一为字符串。
 */
import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'

/** 包装后的请求方法签名：直接返回业务数据（拦截器已剥离 AxiosResponse）。 */
export interface HttpClient {
  get<T>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  delete<T>(url: string, config?: AxiosRequestConfig): Promise<T>
}

/** 从 axios 错误中提取可读消息（FastAPI detail 优先）。 */
function extractError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) {
      // FastAPI 422 校验失败：{ detail: [{ loc, msg }, ...] }
      return detail.map((d) => d.msg).join('；')
    }
    if (typeof detail === 'string' && detail) {
      return detail
    }
    return error.message || '请求失败'
  }
  return error instanceof Error ? error.message : '请求失败'
}

const httpBase: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

httpBase.interceptors.response.use(
  (response) => response.data,
  (error: unknown) => Promise.reject(new Error(extractError(error))),
)

// 运行时拦截器已返回 data，类型上声明为返回业务数据的方法签名
const http = httpBase as unknown as HttpClient

export default http
