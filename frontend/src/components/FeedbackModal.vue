<template>
  <n-modal
    :show="show"
    preset="card"
    title="告诉我们你的想法"
    :style="{ width: '480px', maxWidth: '90vw' }"
    @update:show="(v: boolean) => (show = v)"
  >
    <p class="fb-tip">你的意见会直接影响 TravelPal 的下一个版本，欢迎畅所欲言。</p>
    <div class="fb-form">
      <div class="fb-row">
        <label>称呼</label>
        <n-input v-model:value="form.name" placeholder="怎么称呼你（可选）" clearable />
      </div>
      <div class="fb-row">
        <label>联系方式</label>
        <n-input
          v-model:value="form.contact"
          placeholder="邮箱 / 微信，方便我们回复你（可选）"
          clearable
        />
      </div>
      <div class="fb-row">
        <label>评分</label>
        <n-rate v-model:value="form.rating" />
      </div>
      <div class="fb-row">
        <label>意见</label>
        <n-input
          v-model:value="form.content"
          type="textarea"
          :rows="4"
          placeholder="说说你的使用感受、遇到的问题或建议（必填）"
        />
      </div>
      <div class="fb-actions">
        <n-button type="primary" :loading="submitting" @click="submitFeedback">
          提交反馈
        </n-button>
      </div>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
/** 全局反馈弹窗：从 /about 页问卷抽出，可在任意页面打开（page 自动记录来源路径）。 */
import { ref, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { postFeedback } from '@/services/api'

const show = defineModel<boolean>('show', { default: false })

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
    show.value = false
  } catch (e) {
    message.error(e instanceof Error ? e.message : '提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.fb-tip {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--tp-text-2);
}
.fb-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.fb-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.fb-row label {
  flex-shrink: 0;
  width: 56px;
  font-size: 13px;
  color: var(--tp-text-2);
}
.fb-row .n-input {
  flex: 1;
}
.fb-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
