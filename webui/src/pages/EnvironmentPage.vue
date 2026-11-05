<script setup>
// 环境:GPU(nvidia-smi)、关键包版本,以及完整体检(kohakumoss-doctor,输出在终端)。
import { computed } from 'vue'
import { store, submitJob, togglePin } from '../store.js'

const gpuRows = computed(() => (store.env.gpus || []).map((g, i) => ({
  k: 'gpu ' + i,
  v: g.name + ' · ' + (g.memory_used_mb / 1024).toFixed(1) + '/' + (g.memory_total_mb / 1024).toFixed(1) + ' GB · sm' + g.compute_cap.replace('.', '') + ' · driver ' + g.driver,
  ok: true,
})))
const cards = computed(() => [
  { title: '设备', rows: gpuRows.value.length ? gpuRows.value : [{ k: 'gpu', v: store.env.backend ? '未检测到 NVIDIA GPU' : '后端未连接', ok: false }] },
  {
    title: '运行时',
    rows: [
      { k: 'backend', v: store.env.backend ? '已连接' : '未连接 · 运行 kohakumoss-webui', ok: store.env.backend },
      { k: 'python', v: store.env.python || '—', ok: !!store.env.python },
      { k: 'platform', v: store.env.platform || '—', ok: true },
      ...Object.entries(store.env.packages || {}).map(([k, v]) => ({ k, v: v || '未安装', ok: !!v })),
    ],
  },
])

async function doctor() {
  if (await submitJob('/api/v1/jobs/doctor', {}, '环境体检') && !store.termPinned) togglePin()
}
</script>

<template>
  <div style="animation:pageIn .24s cubic-bezier(.2,.8,.2,1) both;max-width:1280px;margin:0 auto">
    <div style="display:flex;align-items:flex-end;justify-content:space-between;gap:24px;margin-bottom:24px">
      <div>
        <h1 style="margin:0;font-size:20px;line-height:28px;font-weight:600;color:var(--ink)">环境</h1>
        <p style="margin:4px 0 0;font-size:14px;line-height:20px;color:var(--body)">完整体检会列出这台机器缺什么、以及修复命令。</p>
      </div>
      <button @click="doctor" class="hv-fade"
        style="height:36px;padding:0 16px;background:var(--primary);color:var(--on-primary);border:none;border-radius:6px;font-size:14px;font-weight:500;cursor:pointer">环境体检</button>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(400px,1fr));gap:24px">
      <section v-for="c in cards" :key="c.title" style="background:var(--surface);border-radius:8px;box-shadow:var(--shadow-card);padding:16px 20px">
        <h2 style="margin:0 0 14px;font-size:16px;font-weight:600;color:var(--ink)">{{ c.title }}</h2>
        <div v-for="r in c.rows" :key="r.k" style="display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:32px;border-top:1px solid var(--hairline)">
          <span style="font-family:var(--font-mono);font-size:12px;color:var(--mute)">{{ r.k }}</span>
          <span style="display:flex;align-items:center;gap:6px;min-width:0;font-family:var(--font-mono);font-size:13px;color:var(--ink)">
            <span :style="{ width: '6px', height: '6px', borderRadius: '50%', flexShrink: 0, background: r.ok ? 'var(--accent)' : 'var(--warning)' }"></span>
            <span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ r.v }}</span>
          </span>
        </div>
      </section>
    </div>
  </div>
</template>
