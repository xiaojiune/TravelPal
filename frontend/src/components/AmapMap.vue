<template>
  <div ref="container" class="amap-container"></div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  routes: { type: Array, default: () => [] },
  spots: { type: Object, default: () => ({}) },
  highlightDay: { type: Number, default: -1 },
  amapKey: { type: String, default: '' },
})

const container = ref(null)
let map = null
let overlays = []
let amapLoaded = false

function loadAmapScript() {
  return new Promise((resolve) => {
    if (window.AMap) { amapLoaded = true; resolve(); return }
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${props.amapKey}`
    script.onload = () => { amapLoaded = true; resolve() }
    document.head.appendChild(script)
  })
}

function clearOverlays() {
  overlays.forEach(o => map?.remove(o))
  overlays = []
}

function render() {
  if (!map || !props.routes.length || !Object.keys(props.spots).length) return
  clearOverlays()
  const coords = {} // index → [lng, lat]
  Object.entries(props.spots).forEach(([key, s]) => {
    coords[key] = [s.x || s.lon || 0, s.y || s.lat || 0]
  })
  const DAY_COLORS = ['#FF0000', '#FF8C00', '#FFD700', '#00CC00', '#1E90FF', '#8A2BE2', '#00CED1', '#FF1493']
  const spotIds = Object.keys(coords)
  // 添加标记
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
  // 绘制每日路线
  props.routes.forEach((route, di) => {
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
  // 自适应视野
  map.setFitView(null, false, [60, 60, 60, 60])
}

onMounted(async () => {
  if (!props.amapKey) return
  await loadAmapScript()
  if (!amapLoaded) return
  map = new AMap.Map(container.value, {
    zoom: 13,
    resizeEnable: true,
  })
  render()
})

onBeforeUnmount(() => {
  if (map) { map.destroy(); map = null }
})

watch(() => [props.routes, props.spots, props.highlightDay], render, { deep: true })
</script>

<style scoped>
.amap-container { width: 100%; height: 100%; }
</style>
