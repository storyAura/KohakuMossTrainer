// 全局状态与动作:表单(预设层 + 旋钮)、作业跟踪(SSE)、终端、提示。
import { reactive, watch } from 'vue'
import { getJson, postJson, putJson, subscribeJobEvents } from './api.js'
import { KNOB_FIELDS, display, submitted } from './fields.js'
import { initialWatch, startWatching } from './watch.js'

const ACTIVE = ['queued', 'running', 'cancelling']
const KIND_LABEL = { train: '训练', sample: '出图', export: '导出', doctor: '环境体检', download: '下载模型' }

// 作业类型的中文名:数据准备的几个步骤统称「准备数据」
export const kindLabel = kind => KIND_LABEL[kind] || (kind?.startsWith('data:') ? '准备数据' : kind || '')
const TERMINAL = ['succeeded', 'failed', 'cancelled']
const SAMPLE_POLL_MS = 20000
const CHECK_DELAY_MS = 600
const THEME_KEY = 'kohakumoss.theme'
const THEMES = ['system', 'light', 'dark']

export const store = reactive({
  theme: 'light', themePref: 'system', page: 'train', narrow: false, railTab: 'progress',
  caps: { layers: {}, profiles: [], sample_precision: [], weights: '' },
  env: { backend: false, gpus: [], packages: {}, python: '', weights_ready: false, weights: '' },
  // 表单:预设层选择 + 旋钮显示值;dirty = 手动改过的旋钮(切换预设层时不覆盖)
  layers: { algo: 'lora', data: 'kohya', vram: '24g', precision: 'bf16' },
  form: {}, dirty: {}, defaults: {}, datasets: [{ path: '', weight: '1' }],
  lowRam: false, prepare: true,
  adv: {}, collapsed: {}, problems: [], warnings: [], checking: false, checkError: '', banner: null,
  // 当前一组作业(准备数据 → 训练)
  status: 'idle', stage: '', jobId: '', jobs: [], runDir: '', exit: null,
  step: 0, totalSteps: 0, loss: null, lr: null, series: [], samples: [], startedAt: 0, elapsed: 0,
  queue: [], presets: [], runs: [], watch: initialWatch(), weightDirs: [], weightFiles: {},
  logs: [], seq: 0, toasts: [], tSeq: 0, modal: null, configText: '', configPath: '',
  autoScroll: true, atBottom: true, termPinned: false, termFull: false, termOrient: 'h', termOp: 0.92,
})

// ---- 表单 ----

function knobPayload() {
  const out = {}
  for (const f of KNOB_FIELDS) {
    if (f.key in store.form) out[f.key] = submitted(f.type, store.form[f.key])
  }
  return out
}

export function trainForm() {
  return {
    layers: { ...store.layers },
    knobs: knobPayload(),
    datasets: store.datasets.filter(d => d.path.trim()),
    low_ram: store.lowRam,
  }
}

function getKnob(knobs, key) {
  const [top, field] = key.split('.')
  const v = knobs[top]
  return field ? (v && typeof v === 'object' ? v[field] : undefined) : v
}

// 按当前预设层组合向后端取旋钮值,刷新未手动改过的字段
export async function recompose() {
  try {
    const { knobs } = await postJson('/api/v1/compose', { layers: store.layers })
    const form = { ...store.form }
    const defaults = {}
    for (const f of KNOB_FIELDS) {
      defaults[f.key] = display(f.type, getKnob(knobs, f.key))
      if (!store.dirty[f.key]) form[f.key] = defaults[f.key]
    }
    store.defaults = defaults
    store.form = form
  } catch (err) {
    toast('error', '读取预设失败 · ' + err.message)
  }
}

// 改动以预设值为准:改回与预设相同的值不算改动
export function setField(key, value) {
  store.form = { ...store.form, [key]: value }
  const { [key]: _, ...rest } = store.dirty
  store.dirty = key in store.defaults && store.defaults[key] === value ? rest : { ...rest, [key]: true }
  store.banner = null
}

export function resetField(key) {
  const { [key]: _, ...rest } = store.dirty
  store.dirty = rest
  store.form = { ...store.form, [key]: store.defaults[key] ?? '' }
}

export function resetAll() {
  store.dirty = {}
  store.form = { ...store.form, ...store.defaults }
  toast('info', '已恢复为预设值')
}

export function setLayer(group, value) {
  store.layers = { ...store.layers, [group]: value }
  recompose()
}

export function addDataset() { store.datasets = [...store.datasets, { path: '', weight: '1' }] }
export function removeDataset(i) { store.datasets = store.datasets.filter((_, idx) => idx !== i) }
export function setDataset(i, key, val) {
  store.datasets = store.datasets.map((d, idx) => idx === i ? { ...d, [key]: val } : d)
}

export async function previewConfig() {
  try {
    const r = await postJson('/api/v1/config/preview', trainForm())
    store.configText = r.text
    store.configPath = r.path
    Object.assign(store, { problems: r.problems, warnings: r.warnings || [], checkError: '' })
    return r
  } catch (err) {
    toast('error', '配置有误 · ' + err.message)
    return null
  }
}

// 静默校验:表单变动后延迟一会儿向后端预览一次,只更新问题与警告,不弹提示
let checkTimer = null
let checkSeq = 0

async function quietCheck() {
  const seq = ++checkSeq
  store.checking = true
  try {
    const r = await postJson('/api/v1/config/preview', trainForm())
    if (seq !== checkSeq) return
    Object.assign(store, { problems: r.problems, warnings: r.warnings || [], checkError: '' })
  } catch (err) {
    if (seq === checkSeq) Object.assign(store, { problems: [], warnings: [], checkError: err.message })
  } finally {
    if (seq === checkSeq) store.checking = false
  }
}

function scheduleCheck() {
  if (!store.env.backend) return
  clearTimeout(checkTimer)
  checkTimer = setTimeout(quietCheck, CHECK_DELAY_MS)
}

export async function showConfig() {
  if (await previewConfig()) store.modal = 'config'
}

// ---- 作业 ----

const handles = {}

function resetRun() {
  Object.assign(store, {
    step: 0, totalSteps: 0, loss: null, lr: null, series: [], samples: [],
    exit: null, startedAt: Date.now(), elapsed: 0, banner: null,
  })
}

// 训练(可选先准备数据)或只准备数据;prepare 为数据步骤列表
export async function startTrain(prepare, train = true) {
  try {
    const r = await postJson('/api/v1/jobs/train', { ...trainForm(), prepare, train })
    log('dim', '[webui] config ' + r.config)
    track(r.jobs)
    toast('info', train ? '已提交训练' : '已提交数据准备')
  } catch (err) {
    store.banner = { text: err.message }
    log('err', 'ERROR: ' + err.message)
    toast('error', '提交被拒绝 · ' + err.message)
  }
}

export function startRun() { startTrain(store.prepare ? ['inspect', 'text', 'latents'] : []) }
export function prepareData(steps) { startTrain(steps, false) }

// 单个工具作业(出图 / 导出 / 体检 / 下载)
export async function submitJob(path, body, label) {
  try {
    const job = await postJson(path, body)
    track([job])
    toast('info', label + ' 已加入队列')
    return job
  } catch (err) {
    log('err', 'ERROR: ' + err.message)
    toast('error', label + ' 提交失败 · ' + err.message)
    return null
  }
}

function track(jobs) {
  resetRun()
  store.jobs = jobs.map(j => ({ id: j.job_id, kind: j.kind, status: j.status, runDir: j.run_dir }))
  store.status = 'queued'
  store.stage = jobs[0]?.kind || ''
  for (const j of jobs) {
    handles[j.job_id] = subscribeJobEvents(j.job_id, ev => onEvent(j, ev))
  }
}

function onEvent(job, ev) {
  if (ev.type === 'log') return log(ev.kind || 'ink', ev.text)
  if (ev.type === 'progress') return onProgress(job, ev)
  if (ev.type !== 'status') return
  store.jobs = store.jobs.map(j => j.id === job.job_id ? { ...j, status: ev.status } : j)
  if (ev.status === 'running' || ev.status === 'cancelling') {
    Object.assign(store, { status: ev.status, stage: job.kind, jobId: job.job_id, runDir: job.run_dir || store.runDir })
    store.step = 0
    store.totalSteps = 0
  }
  if (!TERMINAL.includes(ev.status)) return
  handles[job.job_id]?.close()
  delete handles[job.job_id]
  if (ev.status === 'failed') {
    store.exit = { line: kindLabel(job.kind) + ' · 退出码 ' + (ev.exit_code ?? '?'), tail: ev.stderr_tail || [] }
    toast('error', kindLabel(job.kind) + '失败 · 退出码 ' + (ev.exit_code ?? '?'))
  }
  if (store.jobs.every(j => TERMINAL.includes(j.status))) finishRun()
}

function onProgress(job, ev) {
  store.step = ev.step
  store.totalSteps = ev.total || store.totalSteps
  store.elapsed = (Date.now() - store.startedAt) / 1000
  if (job.kind !== 'train' || typeof ev.loss !== 'number') return
  const prev = store.series[store.series.length - 1]
  store.loss = ev.loss
  store.lr = ev.lr
  store.series = [...store.series, { x: ev.step, raw: ev.loss, s: prev ? prev.s * 0.9 + ev.loss * 0.1 : ev.loss }].slice(-2000)
}

function finishRun() {
  const failed = store.jobs.find(j => j.status === 'failed')
  const cancelled = store.jobs.some(j => j.status === 'cancelled')
  store.status = failed ? 'failed' : (cancelled ? 'cancelled' : 'succeeded')
  if (store.status === 'succeeded') toast('info', kindLabel(store.jobs[store.jobs.length - 1]?.kind) + '完成')
  refreshSamples()
}

export function askCancel() { store.modal = 'cancel' }
export function closeModal() { store.modal = null }

export async function confirmCancel() {
  store.modal = null
  const live = store.jobs.filter(j => ACTIVE.includes(j.status))
  for (const j of live) await cancelJob(j.id)
}

export async function cancelJob(id) {
  try {
    await postJson('/api/v1/jobs/' + id + '/cancel')
  } catch (err) {
    toast('error', '取消失败 · ' + err.message)
  }
}

export async function loadQueue() {
  try { store.queue = (await getJson('/api/v1/jobs')).jobs } catch { /* 后端未连接 */ }
}

// 训练中定时拉取样图
export const jobActive = () => ACTIVE.includes(store.status)

// 样图跟着监视面板的来源走:本页作业进行中看它的目录,否则看正在监视的运行
export async function refreshSamples() {
  const dir = jobActive() ? store.runDir : (store.watch.run || store.runDir)
  if (!dir) return
  try {
    const r = await getJson('/api/v1/artifacts?run=' + encodeURIComponent(dir))
    store.samples = r.images.slice(0, 6)
  } catch { /* 运行目录尚未创建 */ }
}

// ---- 预设(保存的表单) ----

export async function loadPresets() {
  try { store.presets = (await getJson('/api/v1/presets')).presets } catch { store.presets = [] }
}

export async function savePreset(name) {
  try {
    await putJson('/api/v1/presets/' + encodeURIComponent(name), trainForm())
    toast('info', '预设已保存 · ' + name)
    loadPresets()
  } catch (err) {
    toast('error', '保存失败 · ' + err.message)
  }
}

const LAYER_KEYS = ['algo', 'data', 'vram', 'precision']

// 存档里的旋钮值 -> 表单显示值:v2 存的是提交值,老版扁平存档存的是后端原值
function formValue(field, v, nested) {
  if (!nested) return typeof v === 'string' ? v : display(field.type, v)
  if (field.type === 'lines' && Array.isArray(v)) return v.join('\n')
  if (field.type === 'pixels' && Number.isFinite(+v)) return display('pixels', +v)
  return v
}

// 把一份表单存档写回训练页;认 v2 的 {layers, knobs} 与老版扁平两种格式
async function applyForm(data, label) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('不是 JSON 对象')
  const nested = !!(data.layers || data.knobs)
  const knobs = nested ? (data.knobs || {}) : data
  const layers = nested ? (data.layers || {})
    : Object.fromEntries(LAYER_KEYS.filter(k => k in data).map(k => [k, String(data[k])]))
  store.layers = { ...store.layers, ...layers }
  store.dirty = {}
  await recompose()
  const form = { ...store.form }
  const dirty = {}
  for (const field of KNOB_FIELDS) {
    const v = field.key in knobs ? knobs[field.key] : getKnob(knobs, field.key)
    if (v === undefined) continue
    form[field.key] = formValue(field, v, nested)
    if (form[field.key] !== store.defaults[field.key]) dirty[field.key] = true
  }
  const datasets = Array.isArray(data.datasets) ? data.datasets.filter(d => String(d?.path ?? '').trim())
    .map(d => ({ path: String(d.path).trim(), weight: String(d.weight ?? '1') })) : []
  Object.assign(store, { form, dirty, lowRam: !!data.low_ram, page: 'train' })
  if ('prepare' in data) store.prepare = data.prepare !== false
  store.datasets = datasets.length ? datasets : [{ path: '', weight: '1' }]
  toast('info', '已载入 · ' + label)
}

export async function applyPreset(name) {
  try {
    await applyForm(await getJson('/api/v1/presets/' + encodeURIComponent(name)), '预设 ' + name)
  } catch (err) {
    toast('error', '载入失败 · ' + err.message)
  }
}

// 导出:当前表单下载到浏览器这台电脑(与预设同格式)
export function exportForm() {
  const text = JSON.stringify(trainForm(), null, 1) + '\n'
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' }))
  a.download = (store.form.RUN_NAME || 'config') + '.json'
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}

// 导入:从浏览器这台电脑选一个 .json(v2 或老版格式)
export async function importForm(file) {
  try {
    await applyForm(JSON.parse(await file.text()), file.name)
  } catch (err) {
    toast('error', '导入失败 · ' + err.message)
  }
}

// ---- 终端与提示 ----

export function log(kind, text) {
  store.logs.push({ id: ++store.seq, kind, text })
  if (store.logs.length > 1500) store.logs.splice(0, store.logs.length - 1500)
}

export function toast(kind, text) {
  const id = ++store.tSeq
  store.toasts = [...store.toasts, { id, kind, text }].slice(-3)
  setTimeout(() => dismissToast(id), 5200)
}

export function dismissToast(id) { store.toasts = store.toasts.filter(t => t.id !== id) }
export function copyLogs() {
  navigator.clipboard?.writeText(store.logs.map(l => l.text).join('\n'))
  toast('info', '日志已复制')
}
export function clearLogs() { store.logs = [] }
export function toggleScroll() { store.autoScroll = !store.autoScroll }
export function onLogScroll(e) {
  const el = e.target
  store.atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 24
}
export function termDbl() { store.termFull = !store.termFull }
export function togglePin() { store.termPinned = !store.termPinned; store.termFull = false }
export function toggleOrient() { store.termOrient = store.termOrient === 'h' ? 'v' : 'h' }
export function setTermOp(ev) { store.termOp = Math.max(0.35, Math.min(1, parseInt(ev.target.value, 10) / 100)) }
// 主题:跟随系统 / 浅色 / 深色,记在本机浏览器
const darkQuery = window.matchMedia('(prefers-color-scheme: dark)')

function applyTheme() {
  store.theme = store.themePref === 'system' ? (darkQuery.matches ? 'dark' : 'light') : store.themePref
  document.documentElement.setAttribute('data-theme', store.theme)
}

export function cycleTheme() {
  store.themePref = THEMES[(THEMES.indexOf(store.themePref) + 1) % THEMES.length]
  try { localStorage.setItem(THEME_KEY, store.themePref) } catch { /* 隐私模式 */ }
  applyTheme()
}

function loadTheme() {
  try {
    const saved = localStorage.getItem(THEME_KEY)
    if (THEMES.includes(saved)) store.themePref = saved
  } catch { /* 隐私模式 */ }
  applyTheme()
  darkQuery.addEventListener('change', applyTheme)
}

export function clock(sec) {
  sec = Math.max(0, Math.round(sec))
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60
  const p = n => String(n).padStart(2, '0')
  return h ? h + ':' + p(m) + ':' + p(s) : p(m) + ':' + p(s)
}

// ---- 环境与生命周期 ----

export async function loadEnv() {
  try {
    store.env = { ...(await getJson('/api/v1/environment')), backend: true }
  } catch {
    store.env = { ...store.env, backend: false }
  }
}

// 本机找到的权重目录(WEIGHTS 下拉框的候选)
export async function loadWeightDirs() {
  try { store.weightDirs = (await getJson('/api/v1/weights')).weights } catch { store.weightDirs = [] }
}

// WEIGHTS 指向的 ComfyUI 目录里的 DiT / 文本编码器 / VAE 文件名(三个下拉框的候选)
export async function loadWeightFiles(path) {
  if (!path) { store.weightFiles = {}; return }
  try {
    store.weightFiles = (await getJson('/api/v1/weights/files?path=' + encodeURIComponent(path))).files
  } catch {
    store.weightFiles = {}
  }
}

// 显存档位默认值:不超过本机显存(容差 5%)的最大适配器档位
function vramLayer() {
  const g = store.env.gpus?.[0]
  const sizes = (store.caps.layers.vram || []).map(n => /^(\d+)g$/.exec(n)).filter(Boolean).map(m => +m[1])
  if (!g || !sizes.length) return store.layers.vram
  const fits = sizes.filter(s => g.memory_total_mb / 1024 >= s * 0.95)
  return fits.length ? Math.max(...fits) + 'g' : Math.min(...sizes) + 'g'
}

let timers = []
let onKey = null

export async function init() {
  loadTheme()
  const mq = window.matchMedia('(max-width: 1199px)')
  store.narrow = mq.matches
  mq.addEventListener('change', e => { store.narrow = e.matches })
  onKey = e => {
    if (e.key === 'Escape') {
      if (store.modal) store.modal = null
      else store.termFull = false
    }
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && store.page === 'train') {
      e.preventDefault()
      startRun()
    }
  }
  window.addEventListener('keydown', onKey)
  log('dim', 'KohakuMoss web UI · probing backend')
  await loadEnv()
  if (!store.env.backend) {
    log('warn', 'backend not connected · run: kohakumoss-webui')
    return
  }
  log('ink', 'backend connected · python ' + store.env.python + ' · torch ' + (store.env.packages.torch || '?'))
  store.caps = await getJson('/api/v1/capabilities')
  loadWeightDirs()
  store.layers = { ...store.layers, vram: vramLayer() }
  await recompose()
  if (!store.form.RUN_NAME) store.form = { ...store.form, RUN_NAME: 'my-lora' }
  watch(() => [store.form, store.layers, store.datasets, store.lowRam], scheduleCheck, { immediate: true })
  watch(() => store.form.WEIGHTS, loadWeightFiles, { immediate: true })
  timers = [
    setInterval(loadEnv, 5000),
    setInterval(() => { if ((store.status === 'running' && store.stage === 'train') || store.watch.live) refreshSamples() }, SAMPLE_POLL_MS),
    setInterval(() => { if (ACTIVE.includes(store.status)) store.elapsed = (Date.now() - store.startedAt) / 1000 }, 1000),
    ...startWatching(),
  ]
}

export function destroy() {
  timers.forEach(clearInterval)
  clearTimeout(checkTimer)
  darkQuery.removeEventListener('change', applyTheme)
  for (const id of Object.keys(handles)) handles[id].close()
  if (onKey) window.removeEventListener('keydown', onKey)
}
