<script setup>
// Loss 曲线:读运行目录里的 metrics.jsonl(增量拉取,刷新页面、看以前的运行都在)。
// 每个指标一张图;范围按钮、EMA 平滑、滚轮缩放与拖拽平移(各图联动)。
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import { store, toast } from '../store.js'
import { getJson } from '../api.js'
import { fmtMetric, recentWindow } from '../metrics.js'
import MetricChart from '../components/MetricChart.vue'

const POLL_MS = 3000
const RANGES = [['all', '全部', 100], ['50', '最近 50%', 50], ['20', '最近 20%', 20], ['10', '最近 10%', 10]]
const FIRST = ['loss', 'lr', 'grad_norm']
const NAMES = { loss: 'loss', lr: '学习率 lr', grad_norm: '梯度范数 grad_norm', loss_scale: 'loss scale' }

const runs = ref([])
const run = ref('')
const rows = shallowRef([])
const range = ref('all')
const manual = ref(false)
const smooth = ref(60)
const follow = ref(true)
const picked = ref(new Set(FIRST))
let offset = 0
let timer = null

const keys = computed(() => {
  const all = new Set()
  for (const r of rows.value) for (const k of Object.keys(r)) if (k !== 'step' && k !== 'time') all.add(k)
  return [...FIRST.filter(k => all.has(k)), ...[...all].filter(k => !FIRST.includes(k)).sort()]
})

const series = computed(() => keys.value.filter(k => picked.value.has(k)).map(k => {
  const data = rows.value.filter(r => r[k] !== null && r[k] !== undefined && r.step !== undefined).map(r => [r.step, r[k]])
  const values = data.map(p => p[1])
  return {
    key: k, name: NAMES[k] || k, data, smoothable: /loss/.test(k) && k !== 'loss_scale',
    latest: values.length ? values[values.length - 1] : null,
    min: values.length ? Math.min(...values) : null,
  }
}))

const lossData = computed(() => series.value.find(s => s.key === 'loss')?.data || series.value[0]?.data || [])
const view = computed(() => manual.value ? null : recentWindow(lossData.value, RANGES.find(r => r[0] === range.value)[2]))
const lastStep = computed(() => rows.value.length ? rows.value[rows.value.length - 1].step : '-')

// 默认选中正在训练的那次,否则最新的一次
function preferred(list) {
  const dir = (store.runDir || '').replace(/\\/g, '/')
  return (dir && list.find(r => dir.endsWith('/' + r.path))?.path) || list[0]?.path || ''
}

async function loadRuns() {
  try {
    runs.value = (await getJson('/api/v1/runs')).runs
    if (!run.value || !runs.value.some(r => r.path === run.value)) run.value = preferred(runs.value)
  } catch (err) {
    toast('error', '读取运行列表失败 · ' + err.message)
  }
}

async function poll() {
  if (!run.value) return
  const asked = run.value
  try {
    const r = await getJson('/api/v1/metrics?run=' + encodeURIComponent(asked) + '&offset=' + offset)
    if (asked !== run.value) return
    if (r.reset) rows.value = []
    if (r.rows.length || r.reset) rows.value = rows.value.concat(r.rows)
    offset = r.offset
  } catch { /* 运行目录被删了或后端未连接:下次再试 */ }
}

function setRange(key) {
  range.value = key
  manual.value = false
}

function toggle(k) {
  const next = new Set(picked.value)
  next.has(k) ? next.delete(k) : next.add(k)
  picked.value = next
}

watch(run, () => {
  rows.value = []
  offset = 0
  manual.value = false
  poll()
})

onMounted(async () => {
  await loadRuns()
  timer = setInterval(() => { if (follow.value) poll() }, POLL_MS)
})
onUnmounted(() => clearInterval(timer))

const card = 'background:var(--surface);border-radius:8px;box-shadow:var(--shadow-card);padding:16px'
const chip = on => 'height:28px;padding:0 10px;border-radius:6px;font-family:var(--font-mono);font-size:12px;cursor:pointer;' +
  (on ? 'background:var(--surface);border:1px solid var(--ink);color:var(--ink)' : 'background:transparent;border:1px solid var(--hairline);color:var(--mute)')
</script>

<template>
  <div style="animation:pageIn .24s cubic-bezier(.2,.8,.2,1) both;max-width:1280px;margin:0 auto">
    <h1 style="margin:0;font-size:20px;line-height:28px;font-weight:600;color:var(--ink)">Loss 曲线</h1>
    <p style="margin:4px 0 20px;font-size:14px;line-height:20px;color:var(--body)">读取运行目录里的 metrics.jsonl;滚轮缩放、拖拽平移,各图联动。</p>

    <section :style="card + ';margin-bottom:16px;display:flex;align-items:center;gap:8px;flex-wrap:wrap'">
      <select v-model="run"
        style="flex:1;min-width:260px;height:34px;padding:0 10px;background:var(--surface);border:1px solid var(--hairline);border-radius:6px;font-family:var(--font-mono);font-size:13px;color:var(--ink)">
        <option v-if="!runs.length" value="">还没有带 metrics.jsonl 的运行</option>
        <option v-for="r in runs" :key="r.path" :value="r.path">{{ r.path }}</option>
      </select>
      <button @click="loadRuns" class="hv-border" :style="chip(false)" title="刷新运行列表">↻</button>
      <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--body);cursor:pointer">
        <input type="checkbox" v-model="follow" style="accent-color:var(--ink)" />自动刷新
      </label>
      <span style="flex:1"></span>
      <span style="font-family:var(--font-mono);font-size:12px;color:var(--mute)">step {{ lastStep }} · {{ rows.length }} 行</span>
    </section>

    <section :style="card + ';margin-bottom:16px;display:flex;align-items:center;gap:8px;flex-wrap:wrap'">
      <span style="font-size:12px;color:var(--mute)">范围</span>
      <button v-for="r in RANGES" :key="r[0]" @click="setRange(r[0])" :style="chip(!manual && range === r[0])">{{ r[1] }}</button>
      <button v-if="manual" @click="manual = false" :style="chip(false)">恢复跟随</button>
      <span style="width:1px;height:20px;background:var(--hairline);margin:0 6px"></span>
      <span style="font-size:12px;color:var(--mute)">平滑</span>
      <input type="range" min="0" max="99" v-model.number="smooth" style="width:140px;accent-color:var(--ink)" />
      <span style="font-family:var(--font-mono);font-size:12px;color:var(--ink);min-width:20px">{{ smooth }}</span>
      <span style="width:1px;height:20px;background:var(--hairline);margin:0 6px"></span>
      <span style="font-size:12px;color:var(--mute)">指标</span>
      <button v-for="k in keys" :key="k" @click="toggle(k)" :style="chip(picked.has(k))">{{ k }}</button>
    </section>

    <div v-if="!series.length" :style="card + ';height:160px;display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:12px;color:var(--mute)'">
      {{ run ? '等待第一行指标(每 LOG_EVERY 步写一行)' : '开始训练后,这里显示曲线' }}
    </div>
    <div v-else style="display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:16px">
      <section v-for="s in series" :key="s.key" :style="card">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:8px">
          <div style="font-family:var(--font-mono);font-size:13px;font-weight:600;color:var(--ink)">{{ s.name }}</div>
          <div style="font-family:var(--font-mono);font-size:11px;line-height:16px;color:var(--mute);text-align:right">
            latest <span style="color:var(--ink)">{{ fmtMetric(s.latest) }}</span><br>min <span style="color:var(--ink)">{{ fmtMetric(s.min) }}</span>
          </div>
        </div>
        <MetricChart :name="s.key" :data="s.data" :smooth="smooth" :smoothable="s.smoothable" :window="view" @zoomed="manual = true" />
      </section>
    </div>
  </div>
</template>
