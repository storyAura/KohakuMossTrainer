<script setup>
// 预设:保存 / 载入训练表单(configs/user/webui/<名字>.json,提交训练时自动按运行名保存)。
import { onMounted, ref } from 'vue'
import { store, loadPresets, savePreset, applyPreset } from '../store.js'

const name = ref('')
onMounted(loadPresets)

function save() {
  const n = (name.value || store.form.RUN_NAME || '').trim()
  if (n) savePreset(n)
}
const when = t => new Date(t * 1000).toLocaleString()
</script>

<template>
  <div style="animation:pageIn .24s cubic-bezier(.2,.8,.2,1) both;max-width:960px;margin:0 auto">
    <h1 style="margin:0;font-size:20px;line-height:28px;font-weight:600;color:var(--ink)">预设</h1>
    <p style="margin:4px 0 24px;font-size:14px;line-height:20px;color:var(--body)">保存当前训练页的全部设置;每次开始训练也会按运行名自动存一份。</p>
    <div style="display:flex;gap:8px;margin-bottom:24px">
      <input v-model="name" :placeholder="store.form.RUN_NAME || '预设名'" @keydown.enter="save"
        style="flex:1;height:36px;padding:0 10px;background:var(--surface);border:1px solid var(--hairline);border-radius:6px;font-family:var(--font-mono);font-size:13px;color:var(--ink)" />
      <button @click="save" class="hv-fade"
        style="height:36px;padding:0 16px;background:var(--primary);color:var(--on-primary);border:none;border-radius:6px;font-size:14px;font-weight:500;cursor:pointer">保存当前设置</button>
    </div>
    <section style="background:var(--surface);border-radius:8px;box-shadow:var(--shadow-card);overflow:hidden">
      <div v-if="!store.presets.length" style="height:96px;display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:12px;color:var(--mute)">还没有预设</div>
      <div v-for="p in store.presets" :key="p.name" class="hv-row"
        style="display:flex;align-items:center;gap:12px;padding:0 16px;min-height:44px;border-bottom:1px solid var(--hairline)">
        <span style="flex:1;font-family:var(--font-mono);font-size:13px;color:var(--ink)">{{ p.name }}</span>
        <span style="font-family:var(--font-mono);font-size:12px;color:var(--mute)">{{ when(p.updated) }}</span>
        <button @click="applyPreset(p.name)" class="hv-border"
          style="height:28px;padding:0 10px;background:var(--surface);border:1px solid var(--hairline);border-radius:6px;font-size:12px;color:var(--ink);cursor:pointer">载入</button>
      </div>
    </section>
  </div>
</template>
