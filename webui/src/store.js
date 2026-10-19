// 全局状态与动作:表单(预设层 + 旋钮)、作业跟踪(SSE)、终端、提示。
import { reactive } from 'vue'
import { getJson, postJson, putJson, subscribeJobEvents } from './api.js'
import { KNOB_FIELDS, LAYER_KEYS, display, submitted, toFile, fromFile } from './fields.js'

const ACTIVE = ['queued', 'running', 'cancelling']
const TERMINAL = ['succeeded', 'failed', 'cancelled']
const SAMPLE_POLL_MS = 20000

export const store = reactive({
  theme: 'light', page: 'train', narrow: false, railTab: 'progress',
  caps: { layers: {}, profiles: [], sample_precision: [], config_dir: '' },
  env: { backend: false, gpus: [], packages: {}, python: '', weights: {} },
  // 表单:预设层选择 + 旋钮显示值;dirty = 手动改过的旋钮(切换预设层时不覆盖)
  layers: { algo: 'lora', data: 'kohya', vram: '24g', precision: 'bf16', weights: 'comfy' },
  form: {}, dirty: {}, datasets: [{ path: '', weight: '1' }],
  lowRam: false, prepare: true,
  adv: {}, collapsed: {}, problems: [], banner: null,
  // 当前一组作业(准备数据 → 训练)
  status: 'idle', stage: '', jobId: '', jobs: [], runDir: '', exit: null,
  step: 0, totalSteps: 0, loss: null, lr: null, series: [], samples: [], startedAt: 0, elapsed: 0,
  queue: [], cfgFile: '', cfgFiles: [],
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
    for (const f of KNOB_FIELDS) {
      if (!store.dirty[f.key]) form[f.key] = display(f.type, getKnob(knobs, f.key))
    }
    store.form = form
  } catch (err) {
    toast('error', '读取预设失败 · ' + err.message)
  }
}

export function setField(key, value) {
  store.form = { ...store.form, [key]: value }
  store.dirty = { ...store.dirty, [key]: true }
  store.banner = null
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
    store.problems = r.problems
    return r
  } catch (err) {
    toast('error', '配置有误 · ' + err.message)
    return null
  }
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
    const r = await postJson('/api/v1/jobs/train', { ...trainForm(), prepare, train, snapshot: buildConfig() })
    log('dim', '[webui] config ' + r.config + (r.saved ? ' · form ' + r.saved : ''))
    if (r.saved) store.cfgFile = r.saved
    track(r.jobs)
    toast('info', train ? '已提交训练 · ' + r.jobs.length + ' 个作业' : '已提交数据准备')
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
    store.exit = { line: job.kind + ' · exit_code ' + (ev.exit_code ?? '?'), tail: ev.stderr_tail || [] }
    toast('error', job.kind + ' 失败 · 退出码 ' + (ev.exit_code ?? '?'))
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
  if (store.status === 'succeeded') toast('info', '全部完成 · ' + store.jobs.map(j => j.kind).join(' → '))
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
export async function refreshSamples() {
  if (!store.runDir) return
  try {
    const r = await getJson('/api/v1/artifacts?run=' + encodeURIComponent(store.runDir))
    store.samples = r.images.slice(0, 6)
  } catch { /* 运行目录尚未创建 */ }
}

// ---- 配置文件(kohya_ss 式:整张表单存成扁平 JSON;打开时文件里有的键覆盖,
// 没有的键取所选预设层的值,不认识的键忽略并提示) ----

const CONFIG_VERSION = 1
const EXTRA_KEYS = ['version', 'low_ram', 'prepare', 'datasets']

export function buildConfig() {
  const out = { version: CONFIG_VERSION, low_ram: store.lowRam, prepare: store.prepare }
  for (const k of LAYER_KEYS) out[k] = store.layers[k]
  for (const f of KNOB_FIELDS) {
    if (f.key in store.form) out[f.key] = toFile(f.type, store.form[f.key])
  }
  out.datasets = store.datasets.filter(d => d.path.trim())
  return out
}

// 早期 {layers, knobs, datasets} 嵌套格式 -> 扁平格式
function migrate(data) {
  if (!data.layers && !data.knobs) return data
  const { layers, knobs, low_ram: lowRam, ...rest } = data
  return { ...rest, ...(layers || {}), ...(knobs || {}), low_ram: !!lowRam }
}

// 把配置写回表单;返回被忽略的未知键
export async function applyConfig(raw) {
  const data = migrate(raw)
  const known = new Set([...EXTRA_KEYS, ...LAYER_KEYS, ...KNOB_FIELDS.map(f => f.key)])
  const ignored = Object.keys(data).filter(k => !known.has(k))
  const layers = { ...store.layers }
  for (const k of LAYER_KEYS) if (k in data) layers[k] = String(data[k])
  store.layers = layers
  store.dirty = {}
  await recompose()
  const form = { ...store.form }
  const dirty = {}
  for (const f of KNOB_FIELDS) {
    if (!(f.key in data)) continue
    const v = fromFile(f.type, data[f.key])
    if (v === form[f.key]) continue
    form[f.key] = v
    dirty[f.key] = true
  }
  store.form = form
  store.dirty = dirty
  if ('low_ram' in data) store.lowRam = data.low_ram === true
  if ('prepare' in data) store.prepare = data.prepare !== false
  if (Array.isArray(data.datasets)) {
    const rows = data.datasets.map(d => ({ path: String(d.path ?? ''), weight: String(d.weight ?? '1') }))
    store.datasets = rows.length ? rows : [{ path: '', weight: '1' }]
  }
  return ignored
}

function loadedToast(what, ignored) {
  const note = ignored.length ? ' · 忽略未知字段:' + ignored.join(', ') : ''
  toast(ignored.length ? 'warn' : 'info', '已载入 ' + what + note)
}

const defaultConfigPath = () =>
  (store.caps.config_dir || 'configs/user/webui') + '/' + (store.form.RUN_NAME || 'config') + '.json'

export async function listConfigs() {
  try {
    store.cfgFiles = (await getJson('/api/v1/configs')).files
  } catch {
    store.cfgFiles = []
  }
}

export async function openConfig() {
  const path = store.cfgFile.trim()
  if (!path) return toast('warn', '先填写或选择一个配置文件')
  try {
    const r = await getJson('/api/v1/configs/file?path=' + encodeURIComponent(path))
    loadedToast(path, await applyConfig(r.data))
  } catch (err) {
    toast('error', '打开失败 · ' + err.message)
  }
}

export async function saveConfig() {
  if (!store.cfgFile.trim()) store.cfgFile = defaultConfigPath()
  try {
    const r = await putJson('/api/v1/configs/file?path=' + encodeURIComponent(store.cfgFile.trim()), buildConfig())
    store.cfgFile = r.path
    toast('info', '配置已保存 · ' + r.path)
    listConfigs()
  } catch (err) {
    toast('error', '保存失败 · ' + err.message)
  }
}

// 导出:下载到浏览器所在电脑
export function exportConfig() {
  const text = JSON.stringify(buildConfig(), null, 2) + '\n'
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' }))
  a.download = (store.form.RUN_NAME || 'config') + '.json'
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}

// 导入:从浏览器所在电脑选一个 .json
export async function importConfig(file) {
  try {
    const data = JSON.parse(await file.text())
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('不是 JSON 对象')
    loadedToast(file.name, await applyConfig(data))
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
export function toggleTheme() {
  store.theme = store.theme === 'dark' ? 'light' : 'dark'
  document.documentElement.setAttribute('data-theme', store.theme)
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
  document.documentElement.setAttribute('data-theme', store.theme)
  const mq = window.matchMedia('(max-width: 1199px)')
  store.narrow = mq.matches
  mq.addEventListener('change', e => { store.narrow = e.matches })
  onKey = e => { if (e.key === 'Escape') store.termFull = false }
  window.addEventListener('keydown', onKey)
  log('dim', 'KohakuMoss web UI · probing backend')
  await loadEnv()
  if (!store.env.backend) {
    log('warn', 'backend not connected · run: kohakumoss-webui')
    return
  }
  log('ink', 'backend connected · python ' + store.env.python + ' · torch ' + (store.env.packages.torch || '?'))
  store.caps = await getJson('/api/v1/capabilities')
  store.layers = { ...store.layers, vram: vramLayer() }
  await recompose()
  if (!store.form.RUN_NAME) store.form = { ...store.form, RUN_NAME: 'my-lora' }
  listConfigs()
  timers = [
    setInterval(loadEnv, 5000),
    setInterval(() => { if (store.status === 'running' && store.stage === 'train') refreshSamples() }, SAMPLE_POLL_MS),
    setInterval(() => { if (ACTIVE.includes(store.status)) store.elapsed = (Date.now() - store.startedAt) / 1000 }, 1000),
  ]
}

export function destroy() {
  timers.forEach(clearInterval)
  for (const id of Object.keys(handles)) handles[id].close()
  if (onKey) window.removeEventListener('keydown', onKey)
}
