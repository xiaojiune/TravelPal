<template>
  <div class="page-about">
    <section class="intro">
      <h2>关于 TravelPal</h2>
      <p class="slogan">不占有的陪伴，不缺席的可靠。</p>
      <p class="desc">
        把计算交给机器，把决策留给你——对话式共创 + CA/VNS 双引擎，从一句话到每一程。
      </p>
    </section>

    <section class="feedback-guide">
      <span class="fb-icon">📮</span>
      <div class="fb-text">
        <p class="fb-title">遇到困难？</p>
        <p class="fb-body">欢迎提交反馈，帮助 TravelPal 做得更好。</p>
        <n-button size="small" type="primary" @click="feedbackOpen = true">提交反馈</n-button>
      </div>
    </section>

    <FeedbackModal v-model:show="feedbackOpen" />

    <section class="faq-section">
      <h2>常见问题</h2>
      <n-collapse>
        <n-collapse-item v-for="item in faqs" :key="item.q" :title="item.q">
          <!-- eslint-disable-next-line vue/no-v-html -- faq.md 为项目自管受信内容，Markdown 渲染结果可安全注入 -->
          <div class="faq-answer" v-html="item.a"></div>
        </n-collapse-item>
      </n-collapse>
    </section>
  </div>
</template>

<script setup lang="ts">
/** 关于页：项目介绍 + 反馈入口（内嵌 FeedbackModal，问卷入口已从工具栏迁至本页）+ FAQ 手风琴。 */
import { ref } from 'vue'
import MarkdownIt from 'markdown-it'
import FeedbackModal from '@/components/FeedbackModal.vue'
import faqRaw from '@/content/faq.md?raw'

/** 反馈弹窗显隐：由本页「提交反馈」按钮控制。 */
const feedbackOpen = ref(false)

const md = new MarkdownIt()

/**
 * 解析 faq.md 的 token 流：遇 h2（## 提问）开新项，标题 inline 文本为问题；
 * 其后 block tokens 重组后 render 为答案 HTML。
 */
function parseFaqs(raw: string): { q: string; a: string }[] {
  const tokens = md.parse(raw, {})
  const faqs: { q: string; a: string }[] = []
  let current: string | null = null
  let answerTokens: unknown[] = []
  const flush = () => {
    if (current !== null) {
      const rendered = md.renderer.render(answerTokens as any[], md.options, {})
      faqs.push({ q: current, a: rendered })
    }
    current = null
    answerTokens = []
  }
  for (const token of tokens) {
    if (token.type === 'heading_open' && token.tag === 'h2') {
      flush()
      current = ''
    } else if (current !== null) {
      if (token.type === 'inline' && current === '') {
        current = token.content
      } else {
        answerTokens.push(token)
      }
    }
  }
  flush()
  return faqs
}

const faqs = parseFaqs(faqRaw)
</script>

<style scoped>
.page-about {
  max-width: 860px;
  /* 水平居中：与工作区其它页一致 */
  margin: 0 auto;
  /* 极简布局（无导航/工具轨）下需顶部间距，避免内容紧贴页顶 */
  padding: 48px 16px 24px;
}
.intro {
  margin-bottom: 28px;
}
.intro h2 {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 600;
  color: var(--tp-text);
}
.slogan {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 500;
  color: var(--tp-primary);
}
.desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.8;
  color: var(--tp-text-2);
}
.faq-section h2 {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 600;
  color: var(--tp-text);
}
.faq-answer {
  font-size: 13px;
  line-height: 1.8;
  color: var(--tp-text-2);
}
.faq-answer p {
  margin: 0 0 8px;
}
.faq-answer p:last-child {
  margin-bottom: 0;
}
.faq-answer code {
  background: var(--tp-bg);
  border: 1px solid var(--tp-border-light);
  border-radius: 4px;
  padding: 0 4px;
  font-size: 12px;
}
/* 反馈引导块：靛蓝指示色（与导航「关于项目」着色同色关联，引导用户发现左侧工具栏 📮） */
.feedback-guide {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 28px;
  padding: 14px 16px;
  border: 1px solid var(--tp-info);
  border-radius: 8px;
  background: var(--tp-info-soft);
}
.fb-icon {
  font-size: 22px;
  line-height: 1;
}
.fb-text p {
  margin: 0;
}
.fb-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--tp-info);
  margin-bottom: 4px;
}
.fb-body {
  font-size: 13px;
  line-height: 1.7;
  color: var(--tp-text-2);
}
</style>
