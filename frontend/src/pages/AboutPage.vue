<template>
  <div class="page-about">
    <section class="intro">
      <h2>关于 TravelPal</h2>
      <p class="slogan">不占有的陪伴，不缺席的可靠。</p>
      <p class="desc">
        把计算交给机器，把决策留给你——对话式共创 + CA/VNS 双引擎，从一句话到每一程。
      </p>
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

    <section class="survey-section">
      <h2>告诉我们你的想法</h2>
      <p class="survey-tip">你的意见会直接影响 TravelPal 的下一个版本，欢迎畅所欲言。</p>
      <div class="survey-form">
        <div class="survey-row">
          <label>称呼</label>
          <n-input v-model:value="form.name" placeholder="怎么称呼你（可选）" clearable />
        </div>
        <div class="survey-row">
          <label>联系方式</label>
          <n-input v-model:value="form.contact" placeholder="邮箱 / 微信，方便我们回复你（可选）" clearable />
        </div>
        <div class="survey-row">
          <label>评分</label>
          <n-rate v-model:value="form.rating" />
        </div>
        <div class="survey-row">
          <label>意见</label>
          <n-input
            v-model:value="form.content"
            type="textarea"
            :rows="4"
            placeholder="说说你的使用感受、遇到的问题或建议（必填）"
          />
        </div>
        <div class="survey-actions">
          <n-button type="primary" :loading="submitting" @click="submitFeedback">
            提交反馈
          </n-button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
/** 关于页：项目介绍 + FAQ 手风琴（faq.md 经 markdown-it 切分）+ 用户反馈问卷。 */
import { ref, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import MarkdownIt from 'markdown-it'
import faqRaw from '@/content/faq.md?raw'
import { postFeedback } from '@/services/api'

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

// ================== 反馈问卷 ==================

const route = useRoute()
const message = useMessage()
const submitting = ref(false)
const form = reactive({
  name: '',
  contact: '',
  rating: 0,
  content: '',
})

/** 提交反馈：校验必填 → POST /api/feedback（page 自动记录当前路径）→ 成功后清空表单。 */
async function submitFeedback() {
  if (!form.content.trim()) {
    message.warning('请填写反馈内容')
    return
  }
  submitting.value = true
  try {
    await postFeedback({
      name: form.name.trim() || undefined,
      contact: form.contact.trim() || undefined,
      rating: form.rating || undefined,
      content: form.content.trim(),
      page: route.path,
    })
    message.success('感谢反馈！')
    form.name = ''
    form.contact = ''
    form.rating = 0
    form.content = ''
  } catch (e) {
    message.error(e instanceof Error ? e.message : '提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
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
.survey-section {
  margin-top: 36px;
}
.survey-section h2 {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 600;
  color: var(--tp-text);
}
.survey-tip {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--tp-text-2);
}
.survey-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 560px;
}
.survey-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.survey-row label {
  flex-shrink: 0;
  width: 56px;
  font-size: 13px;
  color: var(--tp-text-2);
}
.survey-row .n-input {
  flex: 1;
}
.survey-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
