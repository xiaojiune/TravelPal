<template>
  <div ref="container" class="cesium-container"></div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  routes: { type: Array, default: () => [] },
  spots: { type: Object, default: () => ({}) },
  highlightDay: { type: Number, default: -1 },
})

const container = ref(null)
let viewer = null
let entities = []

// 基于高德坐标转换算法的 GCJ-02 → WGS-84
function gcj02ToWgs84(lng, lat) {
  const a = 6378245.0; const ee = 0.00669342162296594323
  function transformLat(x, y) {
    let ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x))
    ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0
    ret += (20.0 * Math.sin(y * Math.PI) + 40.0 * Math.sin(y / 3.0 * Math.PI)) * 2.0 / 3.0
    ret += (160.0 * Math.sin(y / 12.0 * Math.PI) + 320.0 * Math.sin(y * Math.PI / 30.0)) * 2.0 / 3.0
    return ret
  }
  function transformLng(x, y) {
    let ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x))
    ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0
    ret += (20.0 * Math.sin(x * Math.PI) + 40.0 * Math.sin(x / 3.0 * Math.PI)) * 2.0 / 3.0
    ret += (150.0 * Math.sin(x / 12.0 * Math.PI) + 300.0 * Math.sin(x / 30.0 * Math.PI)) * 2.0 / 3.0
    return ret
  }
  let dlat = transformLat(lng - 105.0, lat - 35.0)
  let dlng = transformLng(lng - 105.0, lat - 35.0)
  const radlat = lat / 180.0 * Math.PI
  let magic = Math.sin(radlat)
  magic = 1 - ee * magic * magic
  const sqrtmagic = Math.sqrt(magic)
  dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * Math.PI)
  dlng = (dlng * 180.0) / (a / sqrtmagic * Math.cos(radlat) * Math.PI)
  return [lng - dlng, lat - dlat]
}

const DAY_COLORS = [
  Cesium.Color.RED, Cesium.Color.ORANGE, Cesium.Color.YELLOW,
  Cesium.Color.GREEN, Cesium.Color.BLUE, Cesium.Color.PURPLE,
  Cesium.Color.CYAN, Cesium.Color.MAGENTA,
]

function clearEntities() {
  entities.forEach(e => viewer.entities.remove(e))
  entities = []
}

function render() {
  if (!viewer || !props.routes.length || !Object.keys(props.spots).length) return
  clearEntities()
  const spotCoords = {}  // index → [wgsLng, wgsLat]
  Object.entries(props.spots).forEach(([key, s]) => {
    spotCoords[key] = gcj02ToWgs84(s.x || s.lon || 0, s.y || s.lat || 0)
  })
  const positions = Object.values(spotCoords).map(c => Cesium.Cartesian3.fromDegrees(c[0], c[1]))
  // 添加景点标记
  Object.entries(spotCoords).forEach(([key, coord]) => {
    entities.push(viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(coord[0], coord[1]),
      billboard: { image: Cesium.PinBuilder.fromColor(Cesium.Color.BLUE, 32), verticalOrigin: Cesium.VerticalOrigin.BOTTOM },
      label: { text: props.spots[key]?.name || '', font: '12px sans-serif', pixelOffset: new Cesium.Cartesian2(0, 28), showBackground: true },
    }))
  })
  // 绘制每日路径
  let allPositions = []
  props.routes.forEach((route, di) => {
    const pts = route.map(idx => spotCoords[idx]).filter(Boolean)
    if (pts.length < 2) return
    const color = DAY_COLORS[di % DAY_COLORS.length]
    const clamped = props.highlightDay >= 0 && di !== props.highlightDay
    const polyPositions = pts.map(p => Cesium.Cartesian3.fromDegrees(p[0], p[1]))
    allPositions = allPositions.concat(polyPositions)
    entities.push(viewer.entities.add({
      polyline: { positions: polyPositions, width: clamped ? 2 : 4, material: clamped ? color.withAlpha(0.2) : color, clampToGround: true },
    }))
  })
  // 相机定位到所有景点包围盒
  if (allPositions.length) {
    viewer.camera.flyToBoundingSphere(new Cesium.BoundingSphere.fromPoints(allPositions), { duration: 1.5 })
  }
}

onMounted(() => {
  if (!window.Cesium) return
  viewer = new Cesium.Viewer(container.value, {
    animation: false, timeline: false, geocoder: false, homeButton: false,
    navigationHelpButton: false, scene3DOnly: true,
  })
  render()
})

onBeforeUnmount(() => {
  if (viewer) { viewer.destroy(); viewer = null }
})

watch(() => [props.routes, props.spots, props.highlightDay], render, { deep: true })
</script>

<style scoped>
.cesium-container { width: 100%; height: 100%; min-height: 500px; }
</style>
