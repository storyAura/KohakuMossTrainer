<script setup>
// 环境:GPU(nvidia-smi)、关键包版本,以及完整体检(kohakumoss-doctor,输出在终端)。
import { computed } from 'vue'
import { store, submitJob, togglePin } from '../store.js'
import Icon from '../components/Icon.vue'

const gpuRows = computed(() => (store.env.gpus || []).map((g, i) => ({
  k: 'gpu ' + i,
  v: g.name + ' · ' + (g.memory_used_mb / 1024).toFixed(1) + '/' + (g.memory_total_mb / 1024).toFixed(1) + ' GB · sm' + g.compute_cap.replace('.', '') + ' · driver ' + g.driver,
  ok: true,
})))
const cards = computed(() => [
  { title: '设备', icon: 'cpu', rows: gpuRows.value.length ? gpuRows.value : [{ k: 'gpu', v: store.env.backend ? '未检测到 NVIDIA GPU' : '后端未连接', ok: false }] },
  {
    title: '运行时',
    icon: 'layers',
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
  <div class="page">
    <div class="page-head">
      <h1 class="h1">环境</h1>
      <button @click="doctor" class="btn btn-lg btn-primary" :disabled="!store.env.backend"><Icon name="activity" :size="15" />环境体检</button>
    </div>
    <div class="grid">
      <section v-for="c in cards" :key="c.title" class="card card-pad">
        <div class="title"><Icon :name="c.icon" :size="16" /><h2 class="h2">{{ c.title }}</h2></div>
        <div v-for="r in c.rows" :key="r.k" class="row">
          <span class="mono k">{{ r.k }}</span>
          <span class="v">
            <span :class="['chip', r.ok ? 'chip-success' : 'chip-warning']" style="height:18px;padding:0 6px">
              <Icon :name="r.ok ? 'check' : 'alert'" :size="11" />
            </span>
            <span class="mono text">{{ r.v }}</span>
          </span>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 16px; }
.title { display: flex; align-items: center; gap: 8px; color: var(--primary); margin-bottom: 10px; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 42px; border-top: 1px solid var(--hairline-soft); }
.k { font-size: 13px; color: var(--faint); }
.v { display: flex; align-items: center; gap: 8px; min-width: 0; }
.text { font-size: 13.5px; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@media (max-width: 520px) { .grid { grid-template-columns: 1fr; } }
</style>
