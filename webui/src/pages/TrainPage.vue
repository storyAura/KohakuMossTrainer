<script setup>
// 训练页:左侧分组参数卡(fields.js),右侧监控栏(进度/显存、loss 曲线、样图、终端)。
// <1200px 时监控栏折叠为标签页。
import { computed } from 'vue'
import { store, clock, setField, setLayer, showConfig, togglePin } from '../store.js'
import { fileUrl } from '../api.js'
import { GROUPS } from '../fields.js'
import ConfigBar from '../components/ConfigBar.vue'
import ParamCard from '../components/ParamCard.vue'
import StatusBadge from '../components/StatusBadge.vue'
import LossChart from '../components/LossChart.vue'
import TerminalPanel from '../components/TerminalPanel.vue'

const CONTROL = { lines: 'area', json: 'area', list: 'text', pixels: 'num' }

function optionsOf(f, isLayer) {
  if (isLayer) return (store.caps.layers[f.key] || []).map(v => ({ v }))
  if (f.options === 'profiles') return store.caps.profiles.map(v => ({ v }))
  return f.options || []
}

function mkField(f) {
  const isLayer = f.type.startsWith('layer:')
  const v = isLayer ? store.layers[f.key] : (f.special ? store.lowRam : store.form[f.key])
  const type = isLayer ? 'select' : (CONTROL[f.type] || f.type)
  const set = val => {
    if (isLayer) setLayer(f.key, val)
    else if (f.special) store.lowRam = val
    else setField(f.key, val)
  }
  const options = optionsOf(f, isLayer)
  return {
    label: f.label, flag: isLayer ? 'configs/moss/' + f.key : (f.special ? '' : f.key),
    hint: f.hint || '', ph: f.ph || '', value: v ?? '', error: '', options, min: 0, max: 100,
    isPath: type === 'path', isText: type === 'text', isNum: type === 'num', isSelect: type === 'select',
    isArea: type === 'area', isSeg: type === 'seg', isSlider: false, isSecret: false,
    segs: type === 'seg' ? options.map(o => ({ label: o.label || o.v, active: v === o.v, idle: v !== o.v, go: () => set(o.v) })) : [],
    isOn: type === 'toggle' && v === true, isOff: type === 'toggle' && v !== true,
    onInput: ev => set(ev.target.value), onToggle: () => set(!v),
  }
}

const groups = computed(() => GROUPS
  .filter(d => d.hideFor !== store.layers.algo)
  .map(d => {
    const open = !!store.adv[d.key]
    const col = !!store.collapsed[d.key]
    return {
      key: d.key, eyebrow: d.eyebrow, title: d.title, desc: d.desc, custom: d.custom || '',
      fields: d.fields.map(mkField), advFields: d.adv.map(mkField),
      hasAdv: d.adv.length > 0, advOpen: open && d.adv.length > 0,
      advCaret: open ? '▾' : '▸', advLabel: (open ? '收起高级参数' : '高级参数') + ' (' + d.adv.length + ')',
      toggleAdv: () => { store.adv = { ...store.adv, [d.key]: !open } },
      toggleCollapse: () => { store.collapsed = { ...store.collapsed, [d.key]: !col } },
      caretStyle: { flexShrink: 0, marginTop: '4px', fontSize: '12px', color: 'var(--mute)', display: 'inline-block', transform: col ? 'rotate(-90deg)' : 'none', transition: 'transform .26s cubic-bezier(.2,.8,.2,1)' },
      bodyWrapStyle: { display: 'grid', gridTemplateRows: col ? '0fr' : '1fr', margin: '0 -24px', transition: 'grid-template-rows .3s cubic-bezier(.2,.8,.2,1)' },
    }
  }))

const STAGES = { 'data:inspect': '检查数据', 'data:text': '缓存文字', 'data:latents': '缓存图片', train: '训练' }
const running = computed(() => store.status === 'running')
const pct = computed(() => store.totalSteps ? Math.min(100, store.step / store.totalSteps * 100) : 0)
const eta = computed(() => {
  if (!running.value || !store.step || !store.totalSteps || !store.elapsed) return '--:--'
  return clock((store.totalSteps - store.step) * store.elapsed / store.step)
})
const progressLine = computed(() => (STAGES[store.stage] || store.stage || '空闲') +
  ' · ' + store.step + '/' + (store.totalSteps || store.form.STEPS || 0) + ' · ETA ' + eta.value)
const barStyle = computed(() => ({ width: pct.value + '%', height: '6px', background: 'var(--ink)', borderRadius: '6px', transition: 'width .22s linear' }))
const vram = computed(() => {
  const g = store.env.gpus?.[0]
  if (!g) return { pct: 0, warn: false, label: '未检测到 NVIDIA GPU' }
  const p = g.memory_used_mb / g.memory_total_mb * 100
  return { pct: p, warn: p > 92, label: (g.memory_used_mb / 1024).toFixed(1) + ' / ' + (g.memory_total_mb / 1024).toFixed(1) + ' GB · ' + Math.round(p) + '%' }
})
const vramBar = computed(() => ({ width: Math.min(100, vram.value.pct) + '%', height: '6px', background: vram.value.warn ? 'var(--warning)' : 'var(--ink)', borderRadius: '6px', transition: 'width .3s linear' }))
const lossBig = computed(() => store.series.length ? store.series[store.series.length - 1].s.toFixed(4) : '—')

const railTabs = computed(() => [['progress', 'PROGRESS'], ['chart', 'LOSS'], ['samples', 'SAMPLES'], ['logs', 'TERMINAL']]
  .map(t => ({ key: t[0], label: t[1], active: store.railTab === t[0] })))
const show = key => !store.narrow || store.railTab === key
const termAway = computed(() => store.termPinned || store.termFull)
const btn = 'height:36px;padding:0 14px;background:var(--surface);border:1px solid var(--hairline);border-radius:6px;color:var(--ink);font-size:14px;font-weight:500;white-space:nowrap;cursor:pointer'
</script>

<template>
  <div style="animation:pageFade .24s ease none;max-width:1280px;margin:0 auto">
    <div style="display:flex;align-items:flex-end;justify-content:space-between;gap:24px;margin-bottom:24px">
      <div>
        <h1 style="margin:0;font-size:20px;line-height:28px;font-weight:600;color:var(--ink)">训练配置</h1>
        <p style="margin:4px 0 0;font-size:14px;line-height:20px;color:var(--body)">表单写成 configs/user/webui/&lt;运行名&gt;.py,由 kogine 运行;提交前用炉子自带的检查器校验。</p>
      </div>
      <button @click="showConfig" class="hv-border" :style="btn">查看配置</button>
    </div>

    <ConfigBar />

    <div v-if="store.banner"
      style="display:flex;align-items:flex-start;gap:12px;background:var(--error-soft);border:1px solid var(--error);border-radius:8px;padding:12px 16px;margin-bottom:24px;animation:cardIn .2s ease both">
      <span style="width:6px;height:6px;border-radius:50%;background:var(--error);margin-top:7px;flex-shrink:0"></span>
      <div style="flex:1;min-width:0">
        <div style="font-size:14px;font-weight:500;color:var(--ink)">提交被拒绝</div>
        <div style="font-family:var(--font-mono);font-size:12px;line-height:18px;color:var(--body);margin-top:4px;word-break:break-all">{{ store.banner.text }}</div>
      </div>
      <button @click="store.banner = null" style="background:none;border:none;color:var(--mute);cursor:pointer">×</button>
    </div>

    <div v-if="store.exit" style="border:1px solid var(--error);border-radius:8px;overflow:hidden;margin-bottom:24px;animation:cardIn .2s ease both">
      <div style="display:flex;align-items:center;gap:8px;background:var(--error-soft);padding:10px 16px">
        <span style="width:6px;height:6px;border-radius:50%;background:var(--error)"></span>
        <span style="font-size:14px;font-weight:500;color:var(--ink)">作业失败</span>
        <span style="font-family:var(--font-mono);font-size:12px;color:var(--body)">{{ store.exit.line }}</span>
        <span style="flex:1"></span>
        <button @click="store.exit = null" style="background:none;border:none;color:var(--mute);cursor:pointer">×</button>
      </div>
      <div style="background:var(--terminal-bg);padding:12px 16px">
        <div v-for="(l, i) in store.exit.tail" :key="i"
          style="font-family:var(--font-mono);font-size:13px;line-height:20px;color:#ff6166;white-space:pre-wrap;word-break:break-all">{{ l }}</div>
      </div>
    </div>

    <div style="display:flex;flex-wrap:wrap;align-items:flex-start;gap:32px">
      <div style="flex:1 1 620px;min-width:0;max-width:760px;display:flex;flex-direction:column;gap:32px">
        <ParamCard v-for="g in groups" :key="g.key" :g="g" />
      </div>

      <div style="flex:1 1 340px;min-width:320px;max-width:480px;position:sticky;top:88px;display:flex;flex-direction:column;gap:16px">
        <div v-if="store.narrow" style="display:flex;gap:4px;padding:4px;background:var(--surface-2);border-radius:6px">
          <button v-for="t in railTabs" :key="t.key" @click="store.railTab = t.key"
            :style="'flex:1;height:28px;border-radius:6px;font-family:var(--font-mono);font-size:12px;cursor:pointer;' + (t.active ? 'background:var(--surface);border:1px solid var(--hairline);color:var(--ink)' : 'background:transparent;border:1px solid transparent;color:var(--body)')">{{ t.label }}</button>
        </div>

        <section v-if="show('progress')" style="background:var(--surface);border-radius:8px;box-shadow:var(--shadow-card);padding:16px">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
            <div style="font-family:var(--font-mono);font-size:12px;letter-spacing:.5px;color:var(--mute)">PROGRESS</div>
            <StatusBadge :status="store.status" />
          </div>
          <div style="font-family:var(--font-mono);font-size:12px;line-height:16px;color:var(--body);font-variant-numeric:tabular-nums;margin-top:12px">{{ progressLine }}</div>
          <div style="height:6px;background:var(--hairline);border-radius:6px;margin-top:10px"><div :style="barStyle"></div></div>
          <div style="display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-top:16px">
            <div>
              <div style="font-family:var(--font-mono);font-size:28px;line-height:32px;font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums">{{ lossBig }}</div>
              <div style="font-family:var(--font-mono);font-size:12px;color:var(--mute);margin-top:2px">loss (smooth)</div>
            </div>
            <div style="display:grid;grid-template-columns:auto auto;gap:2px 16px;text-align:right;font-family:var(--font-mono);font-size:12px;font-variant-numeric:tabular-nums">
              <span style="color:var(--mute)">lr</span><span style="color:var(--ink)">{{ store.lr ?? store.form.LR }}</span>
              <span style="color:var(--mute)">elapsed</span><span style="color:var(--ink)">{{ clock(store.elapsed) }}</span>
            </div>
          </div>
          <div style="height:1px;background:var(--hairline);margin:16px -16px"></div>
          <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;font-family:var(--font-mono);font-size:12px">
            <span style="color:var(--mute)">VRAM</span><span style="color:var(--ink);font-variant-numeric:tabular-nums">{{ vram.label }}</span>
          </div>
          <div style="height:6px;background:var(--hairline);border-radius:6px;margin-top:8px"><div :style="vramBar"></div></div>
          <div v-if="vram.warn" style="margin-top:10px;background:var(--warning-soft);border-radius:6px;padding:6px 8px;font-size:12px;line-height:16px;color:var(--body)">
            显存吃紧:把「显存档位」调低一档,或打开「省内存模式」。
          </div>
        </section>

        <section v-if="show('chart')" style="background:var(--surface);border-radius:8px;box-shadow:var(--shadow-card);padding:16px">
          <div style="font-family:var(--font-mono);font-size:12px;letter-spacing:.5px;color:var(--mute)">LOSS</div>
          <div style="margin-top:12px"><LossChart /></div>
        </section>

        <section v-if="show('samples')" style="background:var(--surface);border-radius:8px;box-shadow:var(--shadow-card);padding:16px">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
            <div style="font-family:var(--font-mono);font-size:12px;letter-spacing:.5px;color:var(--mute)">SAMPLES</div>
            <span style="font-family:var(--font-mono);font-size:11px;color:var(--mute)">{{ store.samples.length }} 张</span>
          </div>
          <div v-if="!store.samples.length"
            style="height:96px;display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:12px;color:var(--mute);margin-top:12px;border:1px dashed var(--hairline);border-radius:8px">等待第一次采样…</div>
          <div v-else style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px">
            <a v-for="s in store.samples" :key="s.path" :href="fileUrl(s.path)" target="_blank" :title="s.path"
              style="display:block;aspect-ratio:1/1;border:1px solid var(--hairline);border-radius:8px;overflow:hidden;background:var(--surface-2)">
              <img :src="fileUrl(s.path)" style="width:100%;height:100%;object-fit:cover;display:block" />
            </a>
          </div>
        </section>

        <template v-if="show('logs')">
          <section v-if="termAway"
            style="border:1px dashed var(--hairline);border-radius:8px;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;gap:8px">
            <span style="font-family:var(--font-mono);font-size:12px;color:var(--mute)">TERMINAL 已置顶</span>
            <button @click="togglePin" class="hv-line"
              style="height:28px;padding:0 8px;background:transparent;border:1px solid var(--hairline);border-radius:6px;font-family:var(--font-mono);font-size:11px;color:var(--body);cursor:pointer">收回</button>
          </section>
          <TerminalPanel v-else />
        </template>
      </div>
    </div>
  </div>
</template>
