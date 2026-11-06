<script setup>
// 训练页:顶部吸附工具条(分组跳转、改动数、实时校验),左侧分组参数卡(fields.js),
// 右侧监控栏(进度/显存、loss 曲线、样图、终端)。<1200px 时监控栏折叠为标签页。
// 监控来源:本页作业进行中时看作业,否则看磁盘上的运行(命令行启动的也算,watch.js)。
import { computed, ref } from 'vue'
import {
  store, clock, jobActive, setField, setLayer, resetField, resetAll, showConfig, togglePin,
  savePreset, exportForm, importForm, toast,
} from '../store.js'
import { setWatch } from '../watch.js'
import { fileUrl } from '../api.js'
import { GROUPS } from '../fields.js'
import Dropdown from '../components/Dropdown.vue'
import Icon from '../components/Icon.vue'
import ParamCard from '../components/ParamCard.vue'
import StatusBadge from '../components/StatusBadge.vue'
import LossChart from '../components/LossChart.vue'
import TerminalPanel from '../components/TerminalPanel.vue'

const CONTROL = { lines: 'area', list: 'text', pixels: 'num' }

// 保存 / 导入:按运行名存成预设;选中的本机文件写回表单
const picker = ref(null)
function saveCurrent() {
  const name = (store.form.RUN_NAME || '').trim()
  if (name) savePreset(name)
  else toast('warn', '先填写运行名')
}
function onPick(ev) {
  const file = ev.target.files?.[0]
  if (file) importForm(file)
  ev.target.value = ''
}
const fileOptions = part => [{ v: '', label: '自动' }, ...(store.weightFiles[part] || []).map(v => ({ v }))]
const weightOptions = () => store.weightDirs.map(w => ({
  v: w.path, label: w.path, hint: (w.kind === 'hf' ? 'HF' : 'ComfyUI') + (w.moss ? '' : ' · 无 MOSS'),
}))
const escape = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

function optionsOf(f, isLayer) {
  if (isLayer) return (store.caps.layers[f.key] || []).map(v => ({ v }))
  if (f.options === 'profiles') return store.caps.profiles.map(v => ({ v }))
  return f.options || []
}

// 后端问题文本里提到的旋钮名(KNOB.字段 取 KNOB)对应到字段
const knobOf = f => (f.special || f.type.startsWith('layer:')) ? '' : f.key.split('.')[0]
const problemsOf = knob => knob ? store.problems.filter(p => new RegExp('\\b' + escape(knob) + '\\b').test(p)) : []

function mkField(f) {
  const isLayer = f.type.startsWith('layer:')
  const v = isLayer ? store.layers[f.key] : (f.special ? store.lowRam : store.form[f.key])
  const type = isLayer ? 'select' : (CONTROL[f.type] || f.type)
  const set = val => {
    if (isLayer) setLayer(f.key, val)
    else if (f.special) store.lowRam = val
    else setField(f.key, val)
  }
  const options = f.suggest === 'weights' ? weightOptions()
    : f.suggest ? fileOptions(f.suggest) : optionsOf(f, isLayer)
  const knob = !isLayer && !f.special
  return {
    label: f.label, flag: isLayer ? 'configs/moss/' + f.key : (f.special ? '' : f.key),
    hint: f.hint || '', ph: f.ph || '', value: v ?? '', options,
    error: problemsOf(knobOf(f)).join(';'),
    dirty: knob && !!store.dirty[f.key], preset: store.defaults[f.key] ?? '',
    onReset: knob ? () => resetField(f.key) : null,
    isCombo: !!f.suggest, isPath: type === 'path' && !f.suggest, isJson: type === 'json', isText: type === 'text', isNum: type === 'num', isSelect: type === 'select',
    isArea: type === 'area', isSeg: type === 'seg',
    segs: type === 'seg' ? options.map(o => ({ label: o.label || o.v, active: v === o.v, go: () => set(o.v) })) : [],
    isOn: type === 'toggle' && v === true, isOff: type === 'toggle' && v !== true,
    onInput: ev => set(ev.target.value), onPick: set, onToggle: () => set(!v),
  }
}

const visible = computed(() => GROUPS.filter(d => d.hideFor !== store.layers.algo))

const groups = computed(() => visible.value.map(d => {
  const fields = d.fields.map(mkField)
  const advFields = d.adv.map(mkField)
  // 高级参数:没手动开关过时,有问题或有改动就展开;手动开关过就听手动的
  const auto = advFields.some(f => f.error || f.dirty)
  const open = store.adv[d.key] ?? auto
  return {
    key: d.key, eyebrow: d.eyebrow, title: d.title, custom: d.custom || '',
    fields, advFields, collapsed: !!store.collapsed[d.key],
    dirtyCount: [...fields, ...advFields].filter(f => f.dirty).length,
    errorCount: [...fields, ...advFields].filter(f => f.error).length,
    advDirty: advFields.filter(f => f.dirty).length,
    hasAdv: d.adv.length > 0, advOpen: open && d.adv.length > 0,
    advLabel: (open ? '收起高级参数' : '高级参数') + ' (' + d.adv.length + ')',
    toggleAdv: () => { store.adv = { ...store.adv, [d.key]: !open } },
    toggleCollapse: () => { store.collapsed = { ...store.collapsed, [d.key]: !store.collapsed[d.key] } },
  }
}))

const dirtyTotal = computed(() => Object.keys(store.dirty).length)
const attached = computed(() => new Set(groups.value.flatMap(g => [...g.fields, ...g.advFields]).flatMap(f => f.error ? f.error.split(';') : [])))
const looseProblems = computed(() => store.problems.filter(p => !attached.value.has(p)))
const check = computed(() => {
  if (!store.env.backend) return { cls: 'chip-neutral', icon: 'alert', text: '后端未连接' }
  if (store.checkError) return { cls: 'chip-error', icon: 'alert', text: '无法生成配置' }
  if (store.problems.length) return { cls: 'chip-error', icon: 'alert', text: store.problems.length + ' 个问题' }
  if (store.checking) return { cls: 'chip-neutral', icon: 'refresh', text: '检查中…' }
  if (store.warnings.length) return { cls: 'chip-warning', icon: 'alert', text: '可以运行 · ' + store.warnings.length + ' 条提醒' }
  return { cls: 'chip-success', icon: 'check', text: '配置检查通过' }
})

function jump(key) {
  store.collapsed = { ...store.collapsed, [key]: false }
  document.getElementById('group-' + key)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
const jumps = computed(() => groups.value.map(g => ({ key: g.key, title: g.title, dirty: g.dirtyCount, bad: g.errorCount })))
const allCollapsed = computed(() => groups.value.every(g => g.collapsed))
function toggleAll() {
  const shut = !allCollapsed.value
  store.collapsed = Object.fromEntries(groups.value.map(g => [g.key, shut]))
}

// 一次提交(准备数据 + 训练)在界面上只算一个作业:数据步骤统称「准备数据」
const stageOf = kind => kind === 'train' ? '训练中' : (kind?.startsWith('data:') ? '准备数据' : (kind || '空闲'))
const smoothLast = series => series.length ? series[series.length - 1].s.toFixed(4) : '—'
const etaOf = (left, rate) => left > 0 && rate > 0 ? clock(left / rate) : '--:--'

const monitor = computed(() => {
  if (jobActive() || !store.watch.run) {
    const total = store.totalSteps || +store.form.STEPS || 0
    const rate = store.step && store.elapsed ? store.step / store.elapsed : 0
    return {
      source: 'job', status: store.status, stage: jobActive() ? stageOf(store.stage) : '空闲',
      step: store.step, total, series: store.series, loss: smoothLast(store.series),
      lr: store.lr ?? store.form.LR, elapsed: clock(store.elapsed),
      eta: store.status === 'running' ? etaOf(store.totalSteps - store.step, rate) : '--:--',
    }
  }
  const w = store.watch
  const span = w.t0 !== null && w.t1 !== null ? w.t1 - w.t0 : 0
  const rate = span > 0 ? (w.step - w.s0) / span : 0
  return {
    source: 'watch', status: w.live ? 'running' : 'idle', stage: w.live ? '训练中' : '未在运行',
    step: w.step, total: w.total, series: w.series, loss: smoothLast(w.series),
    lr: w.lr ?? '—', elapsed: clock(span), eta: w.live ? etaOf(w.total - w.step, rate) : '--:--',
  }
})
const pct = computed(() => monitor.value.total ? Math.min(100, monitor.value.step / monitor.value.total * 100) : 0)
const runOptions = computed(() => [
  { v: '', label: '自动:跟随最新运行' },
  ...store.runs.map(r => ({ v: r.run, label: r.run, hint: r.live ? '● 运行中' : r.step + (r.total ? ' / ' + r.total : '') + ' 步' })),
])
const watchPick = computed(() => store.watch.pinned ? store.watch.run : '')
const vram = computed(() => {
  const g = store.env.gpus?.[0]
  if (!g) return { pct: 0, warn: false, label: '未检测到 NVIDIA GPU' }
  const p = g.memory_used_mb / g.memory_total_mb * 100
  return { pct: p, warn: p > 92, label: (g.memory_used_mb / 1024).toFixed(1) + ' / ' + (g.memory_total_mb / 1024).toFixed(1) + ' GB' }
})

const railTabs = computed(() => [['progress', '进度'], ['chart', 'Loss'], ['samples', '样图'], ['logs', '终端']]
  .map(t => ({ key: t[0], label: t[1], active: store.railTab === t[0] })))
const show = key => !store.narrow || store.railTab === key
const termAway = computed(() => store.termPinned || store.termFull)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1 class="h1">训练配置</h1>
    </div>

    <div class="toolbar">
      <div class="jumps">
        <span class="eyebrow" style="margin-right:2px">跳到</span>
        <button v-for="j in jumps" :key="j.key" @click="jump(j.key)" class="jump">
          {{ j.title }}<span v-if="j.bad" class="mark bad"></span><span v-else-if="j.dirty" class="mark"></span>
        </button>
        <button class="btn btn-ghost btn-sm" @click="toggleAll">{{ allCollapsed ? '全部展开' : '全部折叠' }}</button>
      </div>
      <div class="toolbar-right">
        <span v-if="dirtyTotal" class="chip chip-warning">已改 {{ dirtyTotal }} 项
          <button class="chip-action" @click="resetAll" data-tip="所有参数恢复为当前预设层的值">全部恢复</button>
        </span>
        <button :class="['chip', check.cls]" @click="showConfig" data-tip="查看将要写入的配置">
          <Icon :name="check.icon" :size="12" />{{ check.text }}
        </button>
        <button @click="showConfig" class="btn btn-sm"><Icon name="file" :size="14" />查看配置</button>
        <button @click="saveCurrent" class="btn btn-sm" :disabled="!store.env.backend" data-tip="按运行名保存为预设(训练机上)"><Icon name="bookmark" :size="14" />保存</button>
        <button @click="exportForm" class="btn btn-sm" data-tip="下载到本机"><Icon name="download" :size="14" />导出</button>
        <button @click="picker.click()" class="btn btn-sm" data-tip="从本机选 .json"><Icon name="folder" :size="14" />导入</button>
        <input ref="picker" type="file" accept=".json,application/json" @change="onPick" hidden />
      </div>
    </div>

    <div v-if="store.banner" class="notice error">
      <Icon name="alert" :size="16" />
      <div class="notice-body">
        <div class="notice-title">提交被拒绝</div>
        <div class="notice-text mono">{{ store.banner.text }}</div>
      </div>
      <button @click="store.banner = null" class="btn btn-ghost btn-sm btn-icon" aria-label="关闭"><Icon name="x" :size="14" /></button>
    </div>

    <div v-if="store.checkError || looseProblems.length || store.warnings.length" class="notice" :class="store.checkError || looseProblems.length ? 'error' : 'warn'">
      <Icon name="alert" :size="16" />
      <div class="notice-body">
        <div class="notice-text mono" v-if="store.checkError">{{ store.checkError }}</div>
        <div v-for="(p, i) in looseProblems" :key="'p' + i" class="notice-text mono">• {{ p }}</div>
        <div v-for="(w, i) in store.warnings" :key="'w' + i" class="notice-text mono warn-line">提醒 · {{ w }}</div>
      </div>
    </div>

    <div v-if="store.exit" class="fail card">
      <div class="fail-head">
        <Icon name="alert" :size="15" />
        <span style="font-weight:600">作业失败</span>
        <span class="mono muted" style="font-size: 13px">{{ store.exit.line }}</span>
        <span style="flex:1"></span>
        <button @click="store.exit = null" class="btn btn-ghost btn-sm btn-icon" aria-label="关闭"><Icon name="x" :size="14" /></button>
      </div>
      <div class="fail-tail">
        <div v-for="(l, i) in store.exit.tail" :key="i">{{ l }}</div>
      </div>
    </div>

    <div class="layout">
      <div class="form-col">
        <ParamCard v-for="g in groups" :key="g.key" :g="g" />
      </div>

      <aside class="side">
        <div v-if="store.narrow" class="seg" style="display:flex">
          <button v-for="t in railTabs" :key="t.key" :class="{ on: t.active }" style="flex:1" @click="store.railTab = t.key">{{ t.label }}</button>
        </div>

        <section v-if="show('progress')" class="card card-pad">
          <div class="card-head">
            <span class="eyebrow">进度</span>
            <StatusBadge :status="monitor.status" />
          </div>
          <div class="source">
            <span v-if="monitor.source === 'job' && jobActive()" class="chip chip-primary"><Icon name="play" :size="12" />本页作业 · {{ store.form.RUN_NAME || 'run' }}</span>
            <Dropdown v-else-if="store.runs.length" :model-value="watchPick" :options="runOptions" @update:model-value="setWatch" class="source-dd" />
            <span v-else class="muted" style="font-size: 14px">runs/ 下还没有训练记录</span>
          </div>
          <div class="stage">
            <span>{{ monitor.stage }}</span>
            <span class="mono">{{ monitor.step }} / {{ monitor.total || '?' }}</span>
          </div>
          <div class="bar" style="margin-top:8px"><div :style="{ width: pct + '%' }"></div></div>
          <div class="stats">
            <div>
              <div class="big mono">{{ monitor.loss }}</div>
              <div class="eyebrow" style="margin-top:2px">loss(平滑)</div>
            </div>
            <div class="kv mono">
              <span>lr</span><b>{{ monitor.lr }}</b>
              <span>已用</span><b>{{ monitor.elapsed }}</b>
              <span>剩余</span><b>{{ monitor.eta }}</b>
            </div>
          </div>
          <div v-if="store.watch.error && monitor.source === 'watch'" class="tip-warn">读取失败:{{ store.watch.error }}</div>
          <div class="divider" style="margin:16px -20px"></div>
          <div class="stage" style="margin-top:0">
            <span class="eyebrow">显存</span><span class="mono">{{ vram.label }}</span>
          </div>
          <div :class="['bar', { warn: vram.warn }]" style="margin-top:8px"><div :style="{ width: Math.min(100, vram.pct) + '%' }"></div></div>
          <div v-if="vram.warn" class="tip-warn">显存吃紧:把「显存档位」调低一档,或打开「省内存模式」。</div>
        </section>

        <section v-if="show('chart')" class="card card-pad">
          <div class="card-head"><span class="eyebrow">Loss</span></div>
          <div style="margin-top:12px"><LossChart :series="monitor.series" :total="monitor.total" /></div>
        </section>

        <section v-if="show('samples')" class="card card-pad">
          <div class="card-head">
            <span class="eyebrow">样图</span>
            <span class="chip chip-neutral">{{ store.samples.length }} 张</span>
          </div>
          <div v-if="!store.samples.length" class="empty" style="margin-top:12px">
            <Icon name="image" :size="18" />等待第一次采样…
          </div>
          <div v-else class="thumbs">
            <a v-for="s in store.samples" :key="s.path" :href="fileUrl(s.path)" target="_blank" :title="s.path" class="thumb">
              <img :src="fileUrl(s.path)" alt="" />
            </a>
          </div>
        </section>

        <template v-if="show('logs')">
          <section v-if="termAway" class="empty" style="flex-direction:row;min-height:52px;justify-content:space-between;padding:0 14px">
            <span>终端已置顶</span>
            <button @click="togglePin" class="btn btn-sm"><Icon name="pin" :size="13" />收回</button>
          </section>
          <TerminalPanel v-else />
        </template>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  position: sticky; top: 56px; z-index: 30; display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  margin: 0 -24px 16px; padding: 10px 24px; background: color-mix(in srgb, var(--canvas) 92%, transparent);
  backdrop-filter: blur(6px); border-bottom: 1px solid var(--hairline-soft);
}
.jumps { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; min-width: 0; }
.jump {
  position: relative; height: 34px; padding: 0 14px; border: 1px solid var(--hairline); border-radius: var(--r-sm);
  background: var(--surface); color: var(--body); font-size: 14px; cursor: pointer; transition: all var(--t-snap) var(--ease);
}
.jump:hover { border-color: var(--primary-line); color: var(--primary); background: var(--primary-soft); }
.mark { position: absolute; top: -4px; right: -4px; width: 9px; height: 9px; border-radius: 50%; background: var(--warning); border: 1.5px solid var(--canvas); }
.mark.bad { background: var(--error); }
.toolbar-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.chip-action { margin-left: 4px; padding: 0 0 0 7px; border: none; border-left: 1px solid var(--warning-line); background: none; color: inherit; font: inherit; cursor: pointer; }
.chip-action:hover { text-decoration: underline; }
.notice { display: flex; align-items: flex-start; gap: 10px; padding: 10px 14px; margin-bottom: 16px; border-radius: var(--r-md); border: 1px solid; animation: rowIn var(--t-base) var(--ease) both; }
.notice > svg { margin-top: 2px; }
.notice.error { background: var(--error-soft); border-color: var(--error-line); color: var(--error-ink); }
.notice.warn { background: var(--warning-soft); border-color: var(--warning-line); color: var(--warning-ink); }
.notice-body { flex: 1; min-width: 0; }
.notice-title { font-weight: 600; font-size: 14px; }
.notice-text { font-size: 14px; line-height: 20px; word-break: break-all; }
.warn-line { color: var(--warning-ink); }
.fail { overflow: hidden; margin-bottom: 16px; border-color: var(--error-line); }
.fail-head { display: flex; align-items: center; gap: 8px; padding: 8px 12px 8px 14px; background: var(--error-soft); color: var(--error-ink); }
.fail-tail { background: var(--terminal-bg); padding: 12px 14px; font-family: var(--font-mono); font-size: 13.5px; line-height: 19px; color: #fda4af; white-space: pre-wrap; word-break: break-all; max-height: 320px; overflow: auto; }
.layout { display: flex; flex-wrap: wrap; align-items: flex-start; gap: 20px; }
.form-col { flex: 1 1 620px; min-width: 0; max-width: 800px; display: flex; flex-direction: column; gap: 14px; }
.side { flex: 1 1 340px; min-width: 320px; max-width: 480px; position: sticky; top: 128px; display: flex; flex-direction: column; gap: 14px; }
.source { margin-top: 12px; display: flex; }
.source-dd { flex: 1; min-width: 0; }
.stage { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 12px; font-size: 14px; color: var(--body); }
.stats { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; margin-top: 14px; }
.big { font-size: 28px; line-height: 34px; font-weight: 600; color: var(--ink); }
.kv { display: grid; grid-template-columns: auto auto; gap: 3px 14px; text-align: right; font-size: 14px; }
.kv span { color: var(--faint); }
.kv b { font-weight: 500; color: var(--ink); }
.tip-warn { margin-top: 10px; padding: 6px 10px; border-radius: var(--r-sm); background: var(--warning-soft); border: 1px solid var(--warning-line); color: var(--warning-ink); font-size: 14px; line-height: 19px; }
.thumbs { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
.thumb { display: block; aspect-ratio: 1 / 1; border: 1px solid var(--hairline); border-radius: var(--r-md); overflow: hidden; background: var(--surface-2); }
.thumb img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform var(--t-base) var(--ease); }
.thumb:hover img { transform: scale(1.03); }
</style>
