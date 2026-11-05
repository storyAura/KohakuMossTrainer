<script setup>
// 作业队列:后端 /api/v1/jobs 的全部作业(串行执行,同一时间只跑一个)。
// 一次提交(准备数据 + 训练)合并成一行:一个名字、一个状态、当前步骤的进度。
import { computed, onMounted, onUnmounted } from 'vue'
import { store, loadQueue, cancelJob, kindLabel } from '../store.js'
import Icon from '../components/Icon.vue'
import StatusBadge from '../components/StatusBadge.vue'

let timer = null
onMounted(() => { loadQueue(); timer = setInterval(loadQueue, 3000) })
onUnmounted(() => clearInterval(timer))

const LIVE = ['queued', 'running', 'cancelling']
const seconds = d => (d || '').split(':').reduce((acc, n) => acc * 60 + (+n || 0), 0)
const clock = s => {
  const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), r = s % 60
  const p = n => String(n).padStart(2, '0')
  return h ? h + ':' + p(m) + ':' + p(r) : p(m) + ':' + p(r)
}

// 合并后的状态:有在跑的算在跑;否则失败 > 取消 > 排队 > 完成
function statusOf(jobs) {
  const has = s => jobs.some(j => j.status === s)
  for (const s of ['cancelling', 'running', 'failed', 'cancelled', 'queued']) if (has(s)) return s
  return 'succeeded'
}

const rows = computed(() => {
  const groups = new Map()
  for (const j of store.queue) {
    const key = j.group || j.job_id
    groups.set(key, [j, ...(groups.get(key) || [])])
  }
  return [...groups.values()].map(jobs => {
    const main = jobs.find(j => j.kind === 'train') || jobs[jobs.length - 1]
    const now = jobs.find(j => j.status === 'running' || j.status === 'cancelling') || main
    const status = statusOf(jobs)
    const preparing = status === 'running' && now.kind.startsWith('data:') && main.kind === 'train'
    const started = jobs.find(j => j.started !== '-')
    const spent = jobs.reduce((acc, j) => acc + seconds(j.duration === '-' ? '' : j.duration), 0)
    return {
      id: jobs[0].job_id, label: kindLabel(main.kind), note: main.note, config: main.config, status,
      stage: preparing ? '准备数据中' : '',
      progress: now.progress, started: started ? started.started : '-', duration: spent ? clock(spent) : '-',
      exit: jobs.find(j => j.status === 'failed')?.exit_code, live: jobs.filter(j => LIVE.includes(j.status)),
    }
  })
})

const progress = p => p.total ? p.step + ' / ' + p.total : '—'
const pct = p => p.total ? Math.min(100, p.step / p.total * 100) : 0

async function stop(row) {
  for (const j of row.live) await cancelJob(j.job_id)
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1 class="h1">作业队列</h1>
      <button class="btn" @click="loadQueue"><Icon name="refresh" :size="15" />刷新</button>
    </div>
    <section class="card" style="overflow-x:auto">
      <div class="grid head">
        <span>作业</span><span>内容</span><span>状态</span><span class="r">进度</span><span class="r">开始</span><span class="r">用时</span><span></span>
      </div>
      <div v-if="!rows.length" class="empty" style="margin:16px">
        <Icon name="queue" :size="20" />还没有作业
      </div>
      <div v-for="r in rows" :key="r.id" class="grid row" :title="r.config">
        <span class="ink strong">{{ r.label }}</span>
        <div style="min-width:0">
          <div class="note mono">{{ r.note }}</div>
          <div v-if="r.stage" class="stage">{{ r.stage }}</div>
        </div>
        <div><StatusBadge :status="r.status" /></div>
        <div class="r prog">
          <div class="mono">{{ progress(r.progress) }}</div>
          <div v-if="r.progress.total" class="bar" style="margin-top:5px;height:5px"><div :style="{ width: pct(r.progress) + '%' }"></div></div>
        </div>
        <span class="mono r">{{ r.started }}</span>
        <span class="mono r">{{ r.duration }}</span>
        <span class="r">
          <button v-if="r.live.length" @click="stop(r)" class="btn btn-sm btn-danger">停止</button>
          <span v-else-if="r.exit" class="chip chip-error">退出码 {{ r.exit }}</span>
        </span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: 110px minmax(180px, 1fr) 110px 130px 80px 80px 96px; gap: 14px; padding: 0 18px; align-items: center; min-width: 820px; }
.head { height: 42px; background: var(--surface-3); border-bottom: 1px solid var(--hairline); font-size: 14px; color: var(--faint); border-radius: var(--r-lg) var(--r-lg) 0 0; }
.row { min-height: 62px; padding-top: 8px; padding-bottom: 8px; border-bottom: 1px solid var(--hairline-soft); font-size: 14px; color: var(--body); transition: background var(--t-snap) var(--ease); }
.row:last-child { border-bottom: none; }
.row:hover { background: var(--surface-3); }
.r { text-align: right; justify-self: end; }
.prog { width: 100%; }
.ink { color: var(--ink); }
.strong { font-weight: 600; font-size: 15px; }
.note { font-size: 14px; line-height: 19px; color: var(--mute); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.stage { font-size: 13.5px; color: var(--primary); margin-top: 2px; }
</style>
