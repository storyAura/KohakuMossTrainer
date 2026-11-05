<script setup>
// 模型:MOSS-Image-Base 权重是否就位,以及一键下载(hf download,约 26 GB)。
import { ref } from 'vue'
import { store, submitJob, togglePin } from '../store.js'

const mirror = ref(false)

async function download() {
  const job = await submitJob('/api/v1/jobs/download', { mirror: mirror.value }, '下载模型')
  if (job && !store.termPinned) togglePin()
}
</script>

<template>
  <div style="animation:pageIn .24s cubic-bezier(.2,.8,.2,1) both;max-width:960px;margin:0 auto">
    <h1 style="margin:0;font-size:20px;line-height:28px;font-weight:600;color:var(--ink)">模型</h1>
    <p style="margin:4px 0 24px;font-size:14px;line-height:20px;color:var(--body)">KohakuMoss 只训练 MOSS-Image;一个目录里有 transformer/、text_encoder/、vae/ 即可。</p>
    <section style="background:var(--surface);border-radius:8px;box-shadow:var(--shadow-card);padding:20px 24px">
      <div style="font-family:var(--font-mono);font-size:12px;letter-spacing:.5px;color:var(--mute)">WEIGHTS</div>
      <h2 style="margin:6px 0 16px;font-size:16px;font-weight:600;color:var(--ink)">OpenMOSS-Team/MOSS-Image-Base</h2>
      <div style="display:flex;align-items:center;gap:8px;font-family:var(--font-mono);font-size:13px">
        <span :style="{ width: '8px', height: '8px', borderRadius: '50%', background: store.env.weights_ready ? 'var(--accent)' : 'var(--warning)' }"></span>
        <span style="color:var(--ink)">{{ store.env.weights }}</span>
        <span style="color:var(--mute)">{{ store.env.weights_ready ? '已就位' : '未下载' }}</span>
      </div>
      <div style="display:flex;align-items:center;gap:16px;margin-top:20px;flex-wrap:wrap">
        <button @click="download" class="hv-fade"
          style="height:36px;padding:0 16px;background:var(--primary);color:var(--on-primary);border:none;border-radius:6px;font-size:14px;font-weight:500;cursor:pointer">{{ store.env.weights_ready ? '重新校验 / 补全下载' : '下载(约 26 GB)' }}</button>
        <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--body);cursor:pointer">
          <input type="checkbox" v-model="mirror" style="accent-color:var(--ink)" />使用 hf-mirror.com 镜像(国内网络)
        </label>
      </div>
      <p style="margin:16px 0 0;font-size:12px;line-height:18px;color:var(--mute)">等同于 <span style="font-family:var(--font-mono)">hf download OpenMOSS-Team/MOSS-Image-Base --local-dir models/MOSS-Image-Base</span>;中断后再点会续传。别的位置的权重直接在训练页「模型权重」填路径。</p>
    </section>
  </div>
</template>
