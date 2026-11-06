<script setup>
// Loss 曲线:读运行目录里的 metrics.jsonl(增量拉取,刷新页面、看以前的运行都在)。
// 每个指标一张图;范围按钮、EMA 平滑、滚轮缩放与拖拽平移(各图联动)。
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import { store, toast } from '../store.js'
import { getJson } from '../api.js'
import { fmtMetric, recentWindow } from '../metrics.js'
import Icon from '../components/Icon.vue'
import MetricChart from '../components/MetricChart.vue'

const POLL_MS = 3000
const RANGES = [['all', '全部', 100], ['50', '最近 50%', 50], ['20', '最近 20%', 20], ['10', '最近 10%', 10]]
const FIRST = ['loss', 'lr', 'grad_norm']
const NAMES = { loss: 'loss', lr: '学习率 lr', grad_norm: '梯度范数 grad_norm', loss_scale: 'loss scale' }
const HIDDEN = ['step', 'time']

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
  for (const r of rows.value) for (const k of Object.keys(r)) if (!HIDDEN.includes(k)) all.add(k)
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

// 默认选中本页正在训练的那次,否则最新的一次
function preferred(list) {
  const dir = (store.runDir || '').replace(/\\/g, '/')
  return (dir && list.find(r => dir.endsWith('/' + r.run))?.run) || list[0]?.run || ''
}

async function loadRuns() {
  try {
    runs.value = (await getJson('/api/v1/runs')).runs
    if (!run.value || !runs.value.some(r => r.run === run.value)) run.value = preferred(runs.value)
  } catch (err) {
    toast('error', '读取运行列表失败 · ' + err.message)
  }
}

async function poll() {
  if (!run.value) return
  const asked = run.value
  try {
    const r = await getJson('/api/v1/runs/metrics?run=' + encodeURIComponent(asked) + '&offset=' + offset)
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
</script>

<template>
  <div class="page" style="max-width:1280px">
    <div class="page-head">
      <h1 class="h1">Loss 曲线</h1>
    </div>

    <section class="card card-pad bar-row">
      <select v-model="run" class="input mono run-pick">
        <option v-if="!runs.length" value="">还没有带 metrics.jsonl 的运行</option>
        <option v-for="r in runs" :key="r.run" :value="r.run">{{ r.run }}{{ r.live ? ' ● 运行中' : '' }}</option>
      </select>
      <button @click="loadRuns" class="btn btn-sm" data-tip="刷新运行列表"><Icon name="refresh" :size="14" /></button>
      <label class="check"><input type="checkbox" v-model="follow" />自动刷新</label>
      <span style="flex:1"></span>
      <span class="mono muted small">step {{ lastStep }} · {{ rows.length }} 行</span>
    </section>

    <section class="card card-pad bar-row">
      <span class="muted small">范围</span>
      <button v-for="r in RANGES" :key="r[0]" @click="setRange(r[0])" :class="['pick', { on: !manual && range === r[0] }]">{{ r[1] }}</button>
      <button v-if="manual" @click="manual = false" class="pick">恢复跟随</button>
      <span class="sep"></span>
      <span class="muted small">平滑</span>
      <input type="range" min="0" max="99" v-model.number="smooth" style="width:140px" />
      <span class="mono small" style="min-width:20px">{{ smooth }}</span>
      <span class="sep"></span>
      <span class="muted small">指标</span>
      <button v-for="k in keys" :key="k" @click="toggle(k)" :class="['pick', { on: picked.has(k) }]">{{ k }}</button>
    </section>

    <div v-if="!series.length" class="card empty" style="height:160px">
      {{ run ? '等待第一行指标(每 LOG_EVERY 步写一行)' : '开始训练后,这里显示曲线' }}
    </div>
    <div v-else class="grid">
      <section v-for="s in series" :key="s.key" class="card card-pad">
        <div class="chart-head">
          <span class="mono name">{{ s.name }}</span>
          <span class="mono muted small" style="text-align:right">
            latest <b>{{ fmtMetric(s.latest) }}</b><br>min <b>{{ fmtMetric(s.min) }}</b>
          </span>
        </div>
        <MetricChart :name="s.key" :data="s.data" :smooth="smooth" :smoothable="s.smoothable" :window="view" @zoomed="manual = true" />
      </section>
    </div>
  </div>
</template>

<style scoped>
.bar-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.run-pick { flex: 1; min-width: 260px; height: 34px; }
.check { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--body); cursor: pointer; }
.small { font-size: 12px; }
.sep { width: 1px; height: 20px; background: var(--hairline); margin: 0 6px; }
.pick { height: 28px; padding: 0 10px; border-radius: 6px; font-family: var(--font-mono); font-size: 12px; cursor: pointer; background: transparent; border: 1px solid var(--hairline); color: var(--mute); }
.pick.on { background: var(--surface); border-color: var(--ink); color: var(--ink); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(520px, 100%), 1fr)); gap: 16px; }
.chart-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 8px; }
.name { font-size: 13px; font-weight: 600; color: var(--ink); }
.chart-head b { color: var(--ink); font-weight: 400; }
</style>
