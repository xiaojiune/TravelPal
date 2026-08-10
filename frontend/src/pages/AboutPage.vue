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
        <p class="fb-body">
          可在任意页面点击左侧工具栏的 📮 按钮进行反馈，提交时会自动附带当前页面，
          帮助我们定位问题所在。
        </p>
      </div>
    </section>

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
/** 关于页：项目介绍 + 反馈引导（指向左侧工具栏 📮）+ FAQ 手风琴（faq.md 经 markdown-it 切分）。 */
import MarkdownIt from 'markdown-it'
import faqRaw from '@/content/faq.md?raw'

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
  margin: 0;
  padding: 0 16px;
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
