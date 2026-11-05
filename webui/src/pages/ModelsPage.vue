<script setup>
// 模型:MOSS-Image-Base 权重是否就位,以及一键下载(hf download,约 26 GB)。
import { ref } from 'vue'
import { store, submitJob, togglePin } from '../store.js'
import Icon from '../components/Icon.vue'

const mirror = ref(false)

async function download() {
  const job = await submitJob('/api/v1/jobs/download', { mirror: mirror.value }, '下载模型')
  if (job && !store.termPinned) togglePin()
}
</script>

<template>
  <div class="page" style="max-width:960px">
    <div class="page-head">
      <h1 class="h1">模型</h1>
    </div>
    <section class="card card-pad">
      <div class="card-head">
        <span class="eyebrow">Weights</span>
        <span v-if="store.env.weights_ready" class="chip chip-success"><Icon name="check" :size="12" />已就位</span>
        <span v-else class="chip chip-warning"><span class="dot"></span>未下载</span>
      </div>
      <h2 class="h2" style="margin-top:6px">OpenMOSS-Team/MOSS-Image-Base</h2>
      <div class="where mono"><Icon name="folder" :size="14" />{{ store.env.weights || '—' }}</div>
      <div class="actions">
        <button @click="download" class="btn btn-lg btn-primary" :disabled="!store.env.backend">
          <Icon name="download" :size="15" />{{ store.env.weights_ready ? '重新校验 / 补全下载' : '下载(约 26 GB)' }}
        </button>
        <label class="check">
          <input type="checkbox" v-model="mirror" />使用 hf-mirror.com 镜像(国内网络)
        </label>
      </div>
    </section>
  </div>
</template>

<style scoped>
.where { display: flex; align-items: center; gap: 6px; margin-top: 10px; padding: 8px 12px; background: var(--surface-3); border: 1px solid var(--hairline-soft); border-radius: var(--r-md); font-size: 13.5px; color: var(--body); }
.actions { display: flex; align-items: center; gap: 16px; margin-top: 16px; flex-wrap: wrap; }
</style>
