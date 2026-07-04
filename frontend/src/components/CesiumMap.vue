<template>
  <div class="cesium-placeholder">
    <div class="placeholder-inner">
      <h3>3D 地图</h3>
      <p>Phase 4 将在此处集成 CesiumJS 3D 地图</p>
      <p class="hint">路径折线、景点标记、自动定位</p>
    </div>
  </div>
</template>

<script setup>
defineProps({ routes: { type: Array, default: () => [] }, spots: { type: Object, default: () => ({}) } })
</script>

<style scoped>
.cesium-placeholder {
  background: #e8f0fe; border: 2px dashed #1a73e8; border-radius: 8px;
  height: 100%; min-height: 500px;
  display: flex; align-items: center; justify-content: center;
}
.placeholder-inner { text-align: center; color: #1a73e8; }
.placeholder-inner h3 { font-size: 18px; margin-bottom: 8px; }
.placeholder-inner p { font-size: 13px; }
.hint { color: #888; margin-top: 4px; }
</style>
