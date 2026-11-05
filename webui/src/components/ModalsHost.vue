<script setup>
// 弹窗:停止作业确认、生成的 kogine 配置预览(含校验问题与提醒)。点遮罩或 Esc 关闭。
import { computed } from 'vue'
import { store, closeModal, confirmCancel, kindLabel, toast } from '../store.js'
import Icon from './Icon.vue'
import StatusBadge from './StatusBadge.vue'

const current = computed(() => store.jobs.find(j => j.kind === 'train') || store.jobs[store.jobs.length - 1])

function copyConfig() {
  navigator.clipboard?.writeText(store.configText)
  toast('info', '配置已复制')
}
function copyCommand() {
  navigator.clipboard?.writeText('kogine run scripts/train/moss.py --config ' + store.configPath)
  toast('info', '命令已复制')
}
</script>

<template>
  <div v-if="store.modal" class="scrim" @click.self="closeModal">
    <div v-if="store.modal === 'cancel'" class="dialog" style="width:480px" role="dialog" aria-modal="true">
      <div class="d-head">
        <span class="d-icon warn"><Icon name="alert" :size="18" /></span>
        <h3 class="h2">停止当前作业?</h3>
      </div>
      <p class="d-text">已保存的检查点会保留。</p>
      <div v-if="current" class="jobs">
        <div class="job">
          <span style="font-weight:600">{{ kindLabel(current.kind) }}</span>
          <span class="mono muted" style="flex:1">{{ store.form.RUN_NAME || 'run' }}</span>
          <StatusBadge :status="store.status" />
        </div>
      </div>
      <div class="d-foot">
        <button @click="closeModal" class="btn btn-lg">继续运行</button>
        <button @click="confirmCancel" class="btn btn-lg btn-danger"><Icon name="stop" :size="14" />停止</button>
      </div>
    </div>

    <div v-if="store.modal === 'config'" class="dialog" style="width:800px" role="dialog" aria-modal="true">
      <div class="d-head">
        <span class="d-icon"><Icon name="file" :size="18" /></span>
        <h3 class="h2" style="flex:1">将要写入的配置</h3>
        <button @click="closeModal" class="btn btn-ghost btn-icon" aria-label="关闭"><Icon name="x" :size="16" /></button>
      </div>
      <div class="path">
        <span class="mono">{{ store.configPath }}</span>
        <button class="link-btn" @click="copyCommand"><Icon name="copy" :size="12" />复制命令行</button>
      </div>
      <div v-if="store.problems.length" class="list error">
        <div v-for="(p, i) in store.problems" :key="i" class="mono">• {{ p }}</div>
      </div>
      <div v-if="store.warnings.length" class="list warn">
        <div v-for="(w, i) in store.warnings" :key="i" class="mono">提醒 · {{ w }}</div>
      </div>
      <pre class="code">{{ store.configText }}</pre>
      <div class="d-foot">
        <button @click="closeModal" class="btn btn-lg">关闭</button>
        <button @click="copyConfig" class="btn btn-lg btn-primary"><Icon name="copy" :size="14" />复制配置</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scrim { position: fixed; inset: 0; z-index: 100; background: var(--scrim); display: flex; align-items: center; justify-content: center; padding: 24px; animation: overlayIn var(--t-base) ease both; }
.dialog { max-width: 100%; max-height: calc(100vh - 48px); overflow: auto; background: var(--surface); border: 1px solid var(--hairline); border-radius: var(--r-xl); box-shadow: var(--shadow-modal); padding: 20px 22px; animation: modalIn var(--t-sheet) var(--ease) both; }
.d-head { display: flex; align-items: center; gap: 10px; }
.d-icon { width: 32px; height: 32px; border-radius: 10px; display: flex; align-items: center; justify-content: center; background: var(--primary-soft); color: var(--primary); }
.d-icon.warn { background: var(--warning-soft); color: var(--warning); }
.d-text { margin: 12px 0 0; font-size: 14px; line-height: 22px; color: var(--body); }
.jobs { margin-top: 14px; border: 1px solid var(--hairline); border-radius: var(--r-md); overflow: hidden; }
.job { display: flex; align-items: center; gap: 12px; padding: 10px 14px; font-size: 14px; border-top: 1px solid var(--hairline-soft); }
.job:first-child { border-top: none; }
.path { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 14px; padding: 8px 12px; background: var(--surface-3); border: 1px solid var(--hairline-soft); border-radius: var(--r-md); font-size: 14px; color: var(--body); }
.list { margin-top: 10px; padding: 8px 12px; border-radius: var(--r-md); border: 1px solid; font-size: 14px; line-height: 20px; }
.list.error { background: var(--error-soft); border-color: var(--error-line); color: var(--error-ink); }
.list.warn { background: var(--warning-soft); border-color: var(--warning-line); color: var(--warning-ink); }
.code { margin: 12px 0 0; background: var(--editor); color: var(--body); border: 1px solid var(--hairline); border-radius: var(--r-md); padding: 14px 16px; max-height: 420px; overflow: auto; font-family: var(--font-mono); font-size: 14px; line-height: 20px; user-select: text; }
.d-foot { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }
</style>
