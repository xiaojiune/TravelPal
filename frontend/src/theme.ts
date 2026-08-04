/** 品牌色板（单一事实来源）：翡翠绿主色 + 靛蓝点缀 + 语义/中性 token。
 * 修改本文件，Naive UI（themeOverrides）与手写 CSS（--tp-* 变量）全站同步生效。
 * light 为当前生效主题；dark 组为深色模式预留（未启用，见 ADR-009 §4）。
 */
export const brandColors = {
  // 主色系（低饱和翡翠绿）
  primary: '#20C997',
  primaryHover: '#2DD4A8',
  primaryPressed: '#14A07A',
  primarySuppl: '#20C997',
  primarySoft: '#E6F7F2',
  // 主色上的小字号文字（WCAG AA：白底对比度≥4.5，#20C997 本身仅 2.8:1）
  primaryText: '#0D8A68',

  // 语义色
  success: '#10B981',
  successSoft: '#E8F8F0',
  warning: '#F59E0B',
  warningSoft: '#FFF6E5',
  error: '#EF4444',
  errorSoft: '#FDECEC',
  // 强调/点缀色（靛蓝，与青绿约 120° 对比，面积 ≤5%：激活导航/图表关键点/AI 标签）
  info: '#6366F1',
  infoSoft: '#EEF0FE',

  // 中性色
  bg: '#F5F5F5',
  surface: '#FFFFFF',
  border: '#E0E0E0',
  borderLight: '#F0F0F0',
  text: '#333333',
  text2: '#666666',
  text3: '#999999',

  // 深色模式（预留，未启用；背景避免纯黑，soft 带青绿倾向保持色调统一）
  dark: {
    bg: '#1A1D21',
    surface: '#14171A',
    primarySoft: '#1A2E2A',
  },
} as const

/** Naive UI 主题覆盖：由 brandColors 生成，主色与语义色对齐品牌板。 */
export const themeOverrides = {
  common: {
    primaryColor: brandColors.primary,
    primaryColorHover: brandColors.primaryHover,
    primaryColorPressed: brandColors.primaryPressed,
    primaryColorSuppl: brandColors.primarySuppl,
    successColor: brandColors.success,
    warningColor: brandColors.warning,
    errorColor: brandColors.error,
    infoColor: brandColors.info,
  },
}

/** 将品牌色写入全局 CSS 变量（--tp-*），供手写样式 var() 引用。挂载前调用避免 FOUC。 */
export function applyThemeVars() {
  const root = document.documentElement.style
  root.setProperty('--tp-primary', brandColors.primary)
  root.setProperty('--tp-primary-hover', brandColors.primaryHover)
  root.setProperty('--tp-primary-pressed', brandColors.primaryPressed)
  root.setProperty('--tp-primary-soft', brandColors.primarySoft)
  root.setProperty('--tp-primary-text', brandColors.primaryText)
  root.setProperty('--tp-success', brandColors.success)
  root.setProperty('--tp-success-soft', brandColors.successSoft)
  root.setProperty('--tp-warning', brandColors.warning)
  root.setProperty('--tp-warning-soft', brandColors.warningSoft)
  root.setProperty('--tp-error', brandColors.error)
  root.setProperty('--tp-error-soft', brandColors.errorSoft)
  root.setProperty('--tp-info', brandColors.info)
  root.setProperty('--tp-info-soft', brandColors.infoSoft)
  root.setProperty('--tp-bg', brandColors.bg)
  root.setProperty('--tp-surface', brandColors.surface)
  root.setProperty('--tp-border', brandColors.border)
  root.setProperty('--tp-border-light', brandColors.borderLight)
  root.setProperty('--tp-text', brandColors.text)
  root.setProperty('--tp-text-2', brandColors.text2)
  root.setProperty('--tp-text-3', brandColors.text3)
  // 深色模式预留变量（当前不启用，定义以保持 token 完整）
  root.setProperty('--tp-bg-dark', brandColors.dark.bg)
  root.setProperty('--tp-surface-dark', brandColors.dark.surface)
  root.setProperty('--tp-primary-soft-dark', brandColors.dark.primarySoft)
}
