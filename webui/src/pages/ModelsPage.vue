<script setup>
// 模型:两种权重格式(ComfyUI 单文件 / HF 文件夹)是否就位,以及一键下载(hf download)。
// 训练页「权重格式」选对应的一种;见 docs/guides/weights.md。
import { computed, ref } from 'vue'
import { store, submitJob, togglePin } from '../store.js'

const mirror = ref(false)
const INFO = {
  comfy: { title: 'ComfyUI 格式(默认)', size: '约 15 GB', note: 'int8 DiT + int8 文本编码器 + 小 VAE,训练默认用它' },
  hf: { title: 'HF 官方格式', size: '约 26 GB', note: 'transformer/ text_encoder/ vae/ 文件夹,训练页权重格式选 hf' },
}
const sets = computed(() => Object.entries(store.env.weights || {}).map(([key, w]) => ({ key, ...w, ...INFO[key] })))

async function download(layout) {
  const job = await submitJob('/api/v1/jobs/download', { layout, mirror: mirror.value }, '下载模型')
  if (job && !store.termPinned) togglePin()
}
</script>

<template>
  <div style="animation:pageIn .24s cubic-bezier(.2,.8,.2,1) both;max-width:960px;margin:0 auto">
    <h1 style="margin:0;font-size:20px;line-height:28px;font-weight:600;color:var(--ink)">模型</h1>
    <p style="margin:4px 0 16px;font-size:14px;line-height:20px;color:var(--body)">任选一种格式下载;别的位置的权重直接在训练页「模型权重」填路径。中断后再点会续传。</p>
    <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--body);cursor:pointer;margin-bottom:24px">
      <input type="checkbox" v-model="mirror" style="accent-color:var(--ink)" />使用 hf-mirror.com 镜像(国内网络)
    </label>
    <div v-if="!sets.length" style="font-size:13px;color:var(--mute)">后端未连接</div>
    <section v-for="w in sets" :key="w.key" style="background:var(--surface);border-radius:8px;box-shadow:var(--shadow-card);padding:20px 24px;margin-bottom:24px">
      <div style="font-family:var(--font-mono);font-size:12px;letter-spacing:.5px;color:var(--mute)">{{ w.key.toUpperCase() }} · {{ w.repo }}</div>
      <h2 style="margin:6px 0 4px;font-size:16px;font-weight:600;color:var(--ink)">{{ w.title }}</h2>
      <p style="margin:0 0 14px;font-size:12px;color:var(--mute)">{{ w.note }}</p>
      <div style="display:flex;align-items:center;gap:8px;font-family:var(--font-mono);font-size:13px">
        <span :style="{ width: '8px', height: '8px', borderRadius: '50%', background: w.ready ? 'var(--accent)' : 'var(--warning)' }"></span>
        <span style="color:var(--ink)">{{ w.dest }}</span>
        <span style="color:var(--mute)">{{ w.ready ? '已就位' : '未下载' }}</span>
      </div>
      <div v-for="f in w.files || []" :key="f" style="font-family:var(--font-mono);font-size:12px;color:var(--mute);margin:4px 0 0 16px">{{ f }}</div>
      <button @click="download(w.key)" class="hv-fade"
        style="margin-top:16px;height:36px;padding:0 16px;background:var(--primary);color:var(--on-primary);border:none;border-radius:6px;font-size:14px;font-weight:500;cursor:pointer">{{ w.ready ? '重新校验 / 补全' : '下载(' + w.size + ')' }}</button>
    </section>
  </div>
</template>
