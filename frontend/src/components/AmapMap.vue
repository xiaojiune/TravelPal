<template>
  <div ref="container" class="amap-container"></div>
</template>

<script setup lang="ts">
/**
 * 高德地图渲染器：绘制景点标记、真实驾车路径（抽稀后）、每日路线着色。
 * 从旧项目 cesium_utils.py 迁移并适配 AMap JS API v2.0。
 *
 * 景点点击弹 InfoWindow 显示行程详情（到达/离开/状态）。
 * 路线支持高亮单日（highlightDay），非高亮日半透明处理。
 */
import { ref, watch, onMounted, onBeforeUnmount, onActivated, nextTick } from 'vue'
import type { SpotDictItem, ScheduleItem } from '@/types'

/** 每日路线配色轮换，避免相邻日颜色冲突。从旧项目 ROUTE_COLORS 迁移。 */
const ROUTE_COLORS = ['#FF3030', '#4169E1', '#32CD32', '#FF8C00', '#9370DB', '#00CED1', '#FFD700', '#FF69B4']

/**
 * 景点 emoji 映射：按名称关键词匹配返回对应 emoji。
 * 优先级按书写顺序（靠前先匹配），无匹配时兜底红点。
 * 从旧项目 cesium_utils.py _getIcon 迁移。
 */
function _getIcon(name: string): string {
  const n = (name || '').toLowerCase()
  if (n.includes('山')) return '\u{1F3D4}'
  if (n.includes('海') || n.includes('湖')) return '\u{1F30A}'
  if (n.includes('公园') || n.includes('园')) return '\u{1F3DE}'
  if (n.includes('寺') || n.includes('庙')) return '\u{1F6D5}'
  if (n.includes('博物馆')) return '\u{1F3DB}'
  if (n.includes('长城')) return '\u{1F3F0}'
  if (n.includes('鸟巢') || n.includes('体育')) return '\u{1F3DF}'
  if (n.includes('故宫') || n.includes('殿')) return '\u{1F3EF}'
  if (n.includes('天坛')) return '\u{1F6D5}'
  if (n.includes('酒店')) return '\u{1F3E8}'
  if (n.includes('步行街') || n.includes('街')) return '\u{1F6CD}'
  if (n.includes('广场')) return '\u{1F3D9}'
  if (n.includes('塔') || n.includes('中心')) return '\u{1F5FC}'
  if (n.includes('河') || n.includes('江')) return '\u{1F3DE}'
  if (n.includes('动物')) return '\u{1F418}'
  if (n.includes('植物')) return '\u{1F33F}'
  if (n.includes('故居') || n.includes('纪念')) return '\u{1F3DB}'
  if (n.includes('岛')) return '\u{1F3DD}'
  if (n.includes('洞') || n.includes('溶洞')) return '\u{1F573}'
  if (n.includes('温泉')) return '\u{2668}'
  if (n.includes('滑雪')) return '\u{26F7}'
  if (n.includes('漂流')) return '\u{1F6F6}'
  if (n.includes('海洋') || n.includes('水族')) return '\u{1F420}'
  if (n.includes('科技')) return '\u{1F52C}'
  return '\u{1F4CD}'
}

/**
 * 解析高德驾车 API 返回的 polyline 字符串。
 * 输入格式："lng,lat;lng,lat;..."（高德标准格式），
 * 返回 [lng, lat] 坐标数组。
 */
function parsePolyline(str: string): [number, number][] {
  return str.split(';').filter(Boolean).map(pair => {
    const [lng, lat] = pair.split(',')
    return [parseFloat(lng), parseFloat(lat)]
  })
}

/** Douglas-Peucker 辅助：点到线段垂距。用于经纬度坐标系，量纲为度。 */
function perpendicularDist(point: [number, number], lineStart: [number, number], lineEnd: [number, number]): number {
  const [x0, y0] = point; const [x1, y1] = lineStart; const [x2, y2] = lineEnd
  const dx = x2 - x1; const dy = y2 - y1
  if (dx === 0 && dy === 0) return Math.sqrt((x0 - x1) ** 2 + (y0 - y1) ** 2)
  const t = Math.max(0, Math.min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx * dx + dy * dy)))
  return Math.sqrt((x0 - (x1 + t * dx)) ** 2 + (y0 - (y1 + t * dy)) ** 2)
}

/**
 * Douglas-Peucker 折线抽稀：在保留形状的前提下减少坐标点数。
 * epsilon=0.0003 对应经纬度约 30m，兼顾精度与性能。
 * 从旧项目 cesium_utils.py douglasPeucker 迁移。
 */
function douglasPeucker(points: [number, number][], epsilon = 0.0003): [number, number][] {
  if (points.length <= 2) return points
  let dmax = 0; let index = 0
  for (let i = 1; i < points.length - 1; i++) {
    const d = perpendicularDist(points[i], points[0], points[points.length - 1])
    if (d > dmax) { dmax = d; index = i }
  }
  if (dmax > epsilon) {
    const left = douglasPeucker(points.slice(0, index + 1), epsilon)
    const right = douglasPeucker(points.slice(index), epsilon)
    return left.slice(0, -1).concat(right)
  }
  return [points[0], points[points.length - 1]]
}

interface Props {
  /** 每日路线列表，每组为景点索引序列（含首尾 depot 0） */
  routes?: number[][]
  /** 景点字典，key 为索引，value 含坐标/名称 */
  spots?: Record<string, SpotDictItem>
  /** 真实路径坐标字典，key 为 "fromIdx_toIdx"，value 为高德 polyline 字符串 */
  polylines?: Record<string, string>
  /** 每日行程表，用于 InfoWindow 点击弹窗 */
  dailySchedules?: ScheduleItem[][]
  /** 高亮某日（索引），-1 表示全部正常显示 */
  highlightDay?: number
  amapKey?: string
  securityCode?: string
}

const props = withDefaults(defineProps<Props>(), {
  routes: () => [],
  spots: () => ({}),
  polylines: () => ({}),
  dailySchedules: () => [],
  highlightDay: -1,
  amapKey: '',
  securityCode: '',
})

const container = ref<HTMLDivElement | null>(null)
let map: any = null
let overlays: any[] = []
let infoWindow: any = null
let amapLoaded = false

/** 动态加载高德 JS API（v2.0），避免重复加载。 */
function loadAmapScript() {
  return new Promise<void>((resolve) => {
    if (window.AMap) { amapLoaded = true; resolve(); return }
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${props.amapKey}`
    script.onload = () => { amapLoaded = true; resolve() }
    document.head.appendChild(script)
  })
}

/** 清除所有覆盖物（标记 + 路径），保持 overlays 列表与地图同步。 */
function clearOverlays() {
  overlays.forEach(o => map?.remove(o))
  overlays = []
}

/**
 * 主渲染入口：绘制景点标记 + InfoWindow + 每日驾车路径。
 * 路径优先使用真实 polylines（经 DP 抽稀），无真实数据时 fallback 到直线。
 */
function render() {
  if (!map || !props.routes.length || !Object.keys(props.spots).length) return
  clearOverlays()
  const coords: Record<string, [number, number]> = {}
  Object.entries(props.spots).forEach(([key, s]: [string, any]) => {
    coords[key] = [s.x || s.lon || 0, s.y || s.lat || 0]
  })

  // 构建景点名→行程项映射，供点击弹窗使用
  const spotScheduleMap: Record<string, ScheduleItem> = {}
  if (props.dailySchedules?.length) {
    for (const day of props.dailySchedules) {
      for (const item of day) {
        if (item.name && item.name !== '酒店（返回）') {
          spotScheduleMap[item.name] = item
        }
      }
    }
  }

  const spotIds = Object.keys(coords)

  // 绘制每个景点的 Marker 标记
  Object.entries(coords).forEach(([key, coord]) => {
    const isHotel = Number(key) === 0
    const spot = props.spots[key]
    const icon = isHotel ? '\u2B50' : _getIcon(spot?.name || '')
    const marker = new AMap.Marker({
      position: coord,
      icon: isHotel
        ? 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png'
        : 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
      offset: new AMap.Pixel(-13, -30),
      label: { content: `${icon} ${spot?.name || ''}`.trim(), offset: new AMap.Pixel(-40, -48) },
    })
    const schedule = spotScheduleMap[spot?.name || '']
    if (schedule) {
      marker.on('click', () => {
        const content = `
          <div style="font-size:13px;line-height:1.6;min-width:160px;">
            <b>${spot?.name}</b><br>
            到达: ${String(Math.floor(schedule.arrival / 60)).padStart(2, '0')}:${String(schedule.arrival % 60).padStart(2, '0')}<br>
            离开: ${schedule.departure > 0 ? String(Math.floor(schedule.departure / 60)).padStart(2, '0') + ':' + String(schedule.departure % 60).padStart(2, '0') : '-'}<br>
            营业时间: ${schedule.tw || '-'}<br>
            到达状态: ${schedule.arrival_status}<br>
            离开状态: ${schedule.departure_status}
          </div>`
        infoWindow.setContent(content)
        infoWindow.open(map, marker.getPosition())
      })
    }
    overlays.push(marker)
    map.add(marker)
  })

  // 绘制每日驾车路径（含抽稀后的真实轨迹）
  ;(props.routes as number[][]).forEach((route, di) => {
    const color = ROUTE_COLORS[di % ROUTE_COLORS.length]
    const clamped = props.highlightDay >= 0 && di !== props.highlightDay
    let pts: [number, number][] = []

    for (let i = 0; i < route.length - 1; i++) {
      const fromIdx = route[i]; const toIdx = route[i + 1]
      const key = `${fromIdx}_${toIdx}`  // 两端索引拼接作为 polylines 字典 key
      if (props.polylines?.[key]) {
        pts.push(...douglasPeucker(parsePolyline(props.polylines[key]), 0.0003))
      } else if (coords[fromIdx]) {
        pts.push(coords[fromIdx])
      }
    }
    const last = coords[route[route.length - 1]]
    if (last) pts.push(last)
    if (pts.length < 2) return

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

  function fitView() {
    if (container.value?.offsetHeight) {
      map.setFitView(null, false, [60, 60, 60, 60])
    } else {
      // 容器零高（如 keep-alive 隐藏）时等 ResizeObserver 触发后再适配
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
  if (props.securityCode && window.AMap) {
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
  infoWindow = new AMap.InfoWindow({ offset: new AMap.Pixel(0, -30) })  // 偏移避免遮挡标记
  console.log('[map] AMap init done, rendering...')
  render()
  map.resize()
})

onBeforeUnmount(() => {
  console.log('[map] unmount')
  if (map) { map.destroy(); map = null }
})

onActivated(() => {
  if (map) nextTick(() => container.value?.offsetHeight && map.resize())
})

// 任意地图数据变化时重新渲染
watch(() => [props.routes, props.spots, props.polylines, props.highlightDay], render, { deep: true })
</script>

<style scoped>
.amap-container { width: 100%; height: 100%; }
</style>
