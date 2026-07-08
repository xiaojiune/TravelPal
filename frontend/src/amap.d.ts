/* eslint-disable @typescript-eslint/no-explicit-any */
// 高德地图 JS API 类型声明（用于 CDN 动态加载，非 npm 包）
declare const AMap: any

interface Window {
  AMap: any
}
