<template>
  <div ref="container" class="amap-container"></div>
</template>

<script setup lang="ts">
/**
 * 高德地图 2D 可视化组件。
 * 接收路线、景点数据，在高德地图上渲染标记和折线。
 *
 * Props:
 *   routes: number[][]            — 每日路径序列，每项为景点索引数组
 *   spots: Record<string, any>    — 景点字典 {idx: {name, x, y, ...}}
 *   highlightDay: number          — 高亮某天（-1 全部显示）
 *   amapKey: string               — 高德 JS API Key
 *   securityCode: string          — 高德 JS API 安全密钥
 */
import { ref, watch, onMounted, onBeforeUnmount, onActivated, nextTick } from 'vue'
import type { SpotDictItem } from '@/types'

interface Props {
  routes?: number[][]
  spots?: Record<string, SpotDictItem>
  highlightDay?: number
  amapKey?: string
  securityCode?: string
}

const props = withDefaults(defineProps<Props>(), {
  routes: () => [],
  spots: () => ({}),
  highlightDay: -1,
  amapKey: '',
  securityCode: '',
})

const container = ref<HTMLDivElement | null>(null)
let map: any = null
let overlays: any[] = []
let amapLoaded = false

/**
 * 动态加载高德 JS API 脚本（首次加载后缓存）。
 * 使用 Promise 保证异步加载完成后才初始化地图。
 */
function loadAmapScript() {
  return new Promise<void>((resolve) => {
    if (window.AMap) { amapLoaded = true; resolve(); return }
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${props.amapKey}`
    script.onload = () => { amapLoaded = true; resolve() }
    document.head.appendChild(script)
  })
}

/** 清除所有覆盖物（标记 + 折线），防止重复渲染。 */
function clearOverlays() {
  overlays.forEach(o => map?.remove(o))
  overlays = []
}

/**
 * 核心渲染函数：添加 POI 标记 → 绘制每日折线 → 自适应视野。
 * 先清空旧覆盖物再重建，避免累积。
 */
function render() {
  if (!map || !props.routes.length || !Object.keys(props.spots).length) return
  clearOverlays()
  const coords: Record<string, [number, number]> = {}
  Object.entries(props.spots).forEach(([key, s]: [string, any]) => {
    coords[key] = [s.x || s.lon || 0, s.y || s.lat || 0]
  })
  const DAY_COLORS = ['#FF0000', '#FF8C00', '#FFD700', '#00CC00', '#1E90FF', '#8A2BE2', '#00CED1', '#FF1493']
  const spotIds = Object.keys(coords)
  // 添加标记：酒店用红色标 (index=0)，景点用蓝色标，icon 源自高德 CDN
  Object.entries(coords).forEach(([key, coord]) => {
    const isHotel = Number(key) === 0
    const marker = new AMap.Marker({
      position: coord,
      icon: isHotel
        ? 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png'
        : 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
      offset: new AMap.Pixel(-13, -30),
      label: { content: props.spots[key]?.name || '', offset: new AMap.Pixel(-40, -48) },
    })
    overlays.push(marker)
    map.add(marker)
  })
  // 绘制每日路线：每天一种颜色取自 fixed 8 色调色板，高亮模式下非当天路线半透明
  ;(props.routes as number[][]).forEach((route, di) => {
    const pts = route.map(idx => coords[idx]).filter(Boolean)
    if (pts.length < 2) return
    const color = DAY_COLORS[di % DAY_COLORS.length]
    const clamped = props.highlightDay >= 0 && di !== props.highlightDay
    const polyline = new AMap.Polyline({
      path: pts,
      strokeColor: color,
      strokeWeight: clamped ? 3 : 5,
      strokeOpacity: clamped ? 0.3 : 0.9,
      strokeStyle: 'solid',
      lineJoin: 'round',
    })
    overlays.push(polyline)
    map.add(polyline)
  })
  // 自适应视野：容器有尺寸时立即 setFitView，否则用 ResizeObserver 等
  function fitView() {
    if (container.value?.offsetHeight) {
      map.setFitView(null, false, [60, 60, 60, 60])
    } else {
      const ro = new ResizeObserver(() => {
        if (container.value?.offsetHeight) {
          ro.disconnect()
          map.setFitView(null, false, [60, 60, 60, 60])
        }
      })
      ro.observe(container.value!)
    }
  }
  nextTick(fitView)
}

onMounted(async () => {
  console.log('[map] mount start, container:', container.value?.offsetHeight)
  if (!props.amapKey) return
  await loadAmapScript()
  if (!amapLoaded) return
  await nextTick()
  if (props.securityCode) {
    window.AMap.securityCode = props.securityCode
  }
  if (container.value?.offsetHeight === 0) {
    console.log('[map] awaiting resize...')
    await new Promise<void>(resolve => {
      const ro = new ResizeObserver(() => {
        if (container.value?.offsetHeight) {
          ro.disconnect()
          resolve()
        }
      })
      ro.observe(container.value!)
    })
  }
  console.log('[map] init AMap, height=' + container.value?.offsetHeight)
  map = new AMap.Map(container.value, {
    zoom: 13,
    resizeEnable: true,
  })
  console.log('[map] AMap init done, rendering...')
  render()
  map.resize()
})

onBeforeUnmount(() => {
  console.log('[map] unmount')
  if (map) { map.destroy(); map = null }
})

/** KeepAlive 重新激活时 AMap 容器已重新挂载到 DOM，强制 resize 恢复瓦片渲染。 */
onActivated(() => {
  if (map) nextTick(() => container.value?.offsetHeight && map.resize())
})

watch(() => [props.routes, props.spots, props.highlightDay], render, { deep: true })
</script>

<style scoped>
.amap-container { width: 100%; height: 100%; }
</style>
