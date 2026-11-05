// 监视磁盘上的训练运行(不管是不是本页启动的):读 <运行目录>/metrics.jsonl 的新增行与 log.txt 的总步数。
// 没有手动选时,自动跟随最新一个正在跑的运行(没有就跟最新一个)。
import { getJson } from './api.js'
import { refreshSamples, store } from './store.js'

const RUNS_POLL_MS = 10000
const ROWS_POLL_MS = 3000
const MAX_POINTS = 2000

const empty = () => ({
  run: '', pinned: false, offset: 0, series: [], step: 0, total: 0, loss: null, lr: null,
  live: false, t0: null, s0: 0, t1: null, error: '',
})

export function initialWatch() { return empty() }

export async function loadRuns() {
  try {
    store.runs = (await getJson('/api/v1/runs')).runs
  } catch {
    store.runs = []
    return
  }
  if (store.watch.pinned) return
  const pick = store.runs.find(r => r.live) || store.runs[0]
  if (pick && pick.run !== store.watch.run) await setWatch(pick.run, false)
}

// 选中一个运行;pinned = 用户手动选的(之后不再自动跟随),run 为空 = 恢复自动
export async function setWatch(run, pinned = true) {
  store.watch = { ...empty(), run, pinned: pinned && !!run }
  if (!run) return loadRuns()
  polling = false
  await pollWatch()
  refreshSamples()
}

function append(series, rows) {
  let prev = series[series.length - 1]
  const added = []
  for (const r of rows) {
    if (typeof r.loss !== 'number') continue
    prev = { x: r.step, raw: r.loss, s: prev ? prev.s * 0.9 + r.loss * 0.1 : r.loss }
    added.push(prev)
  }
  return added.length ? [...series, ...added].slice(-MAX_POINTS) : series
}

// 同一时间只有一个请求在读,免得同一段新增行被追加两次;回来时状态已被换掉(换了运行)就丢弃
let polling = false

export async function pollWatch() {
  const w = store.watch
  if (!w.run || polling) return
  polling = true
  try {
    const r = await getJson('/api/v1/runs/metrics?run=' + encodeURIComponent(w.run) + '&offset=' + w.offset)
    if (store.watch !== w) return
    const base = r.reset ? { ...empty(), run: w.run, pinned: w.pinned } : store.watch
    const rows = r.rows.filter(x => typeof x.step === 'number')
    const first = base.t0 === null ? rows.find(x => typeof x.time === 'number') : null
    const last = rows[rows.length - 1]
    store.watch = {
      ...base,
      offset: r.offset, total: r.total, live: r.live, error: '',
      series: append(base.series, rows),
      step: last ? last.step : (r.step || base.step),
      loss: last?.loss ?? base.loss ?? r.loss, lr: last?.lr ?? base.lr,
      t0: first ? first.time : base.t0, s0: first ? first.step : base.s0,
      t1: last?.time ?? base.t1,
    }
  } catch (err) {
    if (store.watch === w) store.watch = { ...w, error: err.message, live: false }
  } finally {
    polling = false
  }
}

export function startWatching() {
  loadRuns()
  return [
    setInterval(loadRuns, RUNS_POLL_MS),
    setInterval(pollWatch, ROWS_POLL_MS),
  ]
}
