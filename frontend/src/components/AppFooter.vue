<template>
  <footer class="footer">
    <div class="footer-links">
      <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">
        ICP备案/许可证号：桂ICP备2026015614号-1
      </a>
      <span class="footer-sep" aria-hidden="true">·</span>
      <a
        href="https://beian.mps.gov.cn/#/query/webSearch?code=44030002015955"
        target="_blank"
        rel="noopener noreferrer"
        class="footer-beian"
      >
        <svg class="beian-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 2l8 3v6c0 5-3.5 8.5-8 11-4.5-2.5-8-6-8-11V5l8-3z" fill="#2E6FE0" />
          <path
            d="M9 12l2 2 4-4"
            stroke="#fff"
            stroke-width="1.6"
            fill="none"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        粤公网安备 44030002015955号
      </a>
      <span class="footer-sep" aria-hidden="true">·</span>
      <span class="footer-version">v0.2.0</span>
    </div>
  </footer>
</template>

<script setup lang="ts">
/**
 * 全局页脚：ICP/公安备案 + 版本号。全站所有界面（门户/工作区/认证/关于）统一展示，
 * 备案信息为合规要求，单一来源在此组件，避免各页重复维护。
 */
defineOptions({ name: 'AppFooter' })
</script>

<style scoped>
.footer {
  text-align: center;
  padding: 16px;
  color: var(--tp-text-3);
  font-size: 12px;
}
.footer a {
  color: var(--tp-text-3);
  text-decoration: none;
}
.footer-links {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}
.footer-sep {
  color: var(--tp-text-3);
  opacity: 0.6;
}
.footer-beian {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.beian-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}
.footer-version {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border: 1px solid var(--tp-border);
  border-radius: 10px;
  color: var(--tp-text-3);
  font-size: 11px;
  line-height: 1.4;
}
</style>
