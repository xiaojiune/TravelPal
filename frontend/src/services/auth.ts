/** 认证 API 客户端：注册 / 登录 / 登出 / 当前用户（基于统一 http 实例）。

  浏览器与后端同源（dev: Vite 代理 /api；生产: Nginx 反代 /api），httpOnly Cookie
  自动携带，无需在此处理 Authorization/凭据。类型由 OpenAPI 生成（types.generated.ts）。
  */
import type { components } from '@/api/types.generated'
import type { UserOut } from '@/types'
import http from '@/services/http'

type AuthLogin = components['schemas']['AuthLogin']
type AuthRegister = components['schemas']['AuthRegister']

/**
 * 登录：校验凭证并创建服务端会话（后端 Set-Cookie httpOnly），返回当前用户。
 * @param data - { email, password }
 */
export function postAuthLogin(data: AuthLogin): Promise<UserOut> {
  return http.post('/auth/login', data)
}

/**
 * 注册：创建账号并自动登录，返回当前用户。
 * @param data - { email, password, nickname? }
 */
export function postAuthRegister(data: AuthRegister): Promise<UserOut> {
  return http.post('/auth/register', data)
}

/**
 * 登出：撤销服务端会话并清除 Cookie。
 */
export function postAuthLogout(): Promise<{ ok: boolean }> {
  return http.post('/auth/logout')
}

/**
 * 获取当前登录用户；未登录时后端返回 401（http 拦截器会转为 Error 抛出，
 * 调用方按「未登录」捕获处理）。
 */
export function getAuthMe(): Promise<UserOut> {
  return http.get('/auth/me')
}
