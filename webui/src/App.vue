<script setup>
// 应用壳:顶栏(运行名 / GPU / 主题 / 开始与停止)、侧栏导航、页面切换、提示栈、
// 置顶悬浮终端(跨页面常驻)、弹窗宿主。
import { computed, onMounted, onUnmounted } from 'vue'
import { store, init, destroy, toggleTheme, startRun, askCancel, dismissToast } from './store.js'
import StatusBadge from './components/StatusBadge.vue'
import TerminalPanel from './components/TerminalPanel.vue'
import ModalsHost from './components/ModalsHost.vue'
import TrainPage from './pages/TrainPage.vue'
import ToolsPage from './pages/ToolsPage.vue'
import LossPage from './pages/LossPage.vue'
import QueuePage from './pages/QueuePage.vue'
import ArtifactsPage from './pages/ArtifactsPage.vue'
import ModelsPage from './pages/ModelsPage.vue'
import EnvironmentPage from './pages/EnvironmentPage.vue'

onMounted(init)
onUnmounted(destroy)

const PAGES = {
  train: ['训练', TrainPage], loss: ['Loss 曲线', LossPage], tools: ['出图 / 导出', ToolsPage], queue: ['队列', QueuePage],
  artifacts: ['产物', ArtifactsPage], models: ['模型', ModelsPage],
  env: ['环境', EnvironmentPage],
}
const nav = computed(() => Object.entries(PAGES).map(([key, [label]]) => ({ key, label, active: store.page === key })))
const page = computed(() => (PAGES[store.page] || PAGES.train)[1])

const busy = computed(() => ['queued', 'running', 'cancelling'].includes(store.status))
const gpu = computed(() => {
  const g = store.env.gpus?.[0]
  if (!g) return { label: store.env.backend ? 'GPU 未检测' : '后端未连接', warn: !store.env.backend }
  const used = g.memory_used_mb / 1024, total = g.memory_total_mb / 1024
  const name = g.name.replace(/NVIDIA\s*/i, '').replace(/GeForce\s*/i, '')
  return { label: name + ' · ' + used.toFixed(1) + '/' + total.toFixed(1) + ' GB', warn: used / total > 0.92 }
})
const runLabel = computed(() => [store.form.RUN_NAME || 'run', store.layers.algo, store.layers.vram, store.layers.precision].join(' · '))
const mainPad = computed(() => {
  if (!store.termPinned || store.termFull) return {}
  return store.termOrient === 'v' ? { paddingRight: '472px' } : { paddingBottom: '268px' }
})
const DOT = { error: 'var(--error)', warn: 'var(--warning)', info: 'var(--accent)' }
</script>

<template>
  <div style="min-height:100vh;background:var(--canvas);color:var(--ink);font-family:var(--font-sans)">
    <header style="position:sticky;top:0;z-index:40;height:56px;display:flex;align-items:center;gap:16px;padding:0 24px;background:var(--surface);border-bottom:1px solid var(--hairline)">
      <div style="display:flex;align-items:baseline;gap:6px">
        <span style="font-size:15px;font-weight:600;letter-spacing:-0.2px;color:var(--ink)">KohakuMoss</span>
        <span style="font-family:var(--font-mono);font-size:12px;color:var(--mute)">webui</span>
      </div>
      <div style="width:1px;height:20px;background:var(--hairline)"></div>
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--mute);border:1px solid var(--hairline);border-radius:6px;padding:1px 6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ runLabel }}</span>
      <div style="flex:1"></div>
      <span :style="{ fontFamily: 'var(--font-mono)', fontSize: '12px', borderRadius: '6px', padding: '3px 8px', whiteSpace: 'nowrap', color: gpu.warn ? 'var(--warning)' : 'var(--body)', background: gpu.warn ? 'var(--warning-soft)' : 'transparent', border: gpu.warn ? 'none' : '1px solid var(--hairline)' }">{{ gpu.label }}</span>
      <button @click="toggleTheme" class="hv-line"
        style="height:32px;padding:0 10px;background:transparent;border:1px solid var(--hairline);border-radius:6px;cursor:pointer;font-family:var(--font-mono);font-size:12px;color:var(--body)">{{ store.theme === 'dark' ? '暗色' : '亮色' }}</button>
      <button @click="startRun" class="hv-fade" :title="busy ? '会排在当前作业之后' : ''"
        style="height:36px;padding:0 16px;background:var(--primary);color:var(--on-primary);border:none;border-radius:6px;font-size:14px;font-weight:500;white-space:nowrap;cursor:pointer">{{ busy ? '加入队列' : '开始训练' }}</button>
      <button v-if="busy" @click="askCancel" class="hv-danger"
        style="height:36px;padding:0 16px;background:var(--surface);color:var(--error);border:1px solid var(--error);border-radius:6px;font-size:14px;font-weight:500;white-space:nowrap;cursor:pointer">停止</button>
    </header>

    <div style="display:flex;align-items:stretch;min-height:calc(100vh - 56px)">
      <aside style="flex:0 0 200px;border-right:1px solid var(--hairline);padding:24px 0;position:sticky;top:56px;align-self:flex-start;height:calc(100vh - 56px)">
        <nav style="display:flex;flex-direction:column">
          <button v-for="n in nav" :key="n.key" @click="store.page = n.key" :class="n.active ? '' : 'hv-nav'"
            :style="'display:flex;align-items:center;height:36px;padding:0 24px;border:none;cursor:pointer;text-align:left;font-size:14px;transition:background .14s ease,color .14s ease;' + (n.active ? 'background:var(--surface-2);border-left:2px solid var(--ink);color:var(--ink);font-weight:500' : 'background:transparent;border-left:2px solid transparent;color:var(--body)')">{{ n.label }}</button>
        </nav>
        <div style="margin-top:32px;padding:0 24px">
          <div style="font-family:var(--font-mono);font-size:12px;letter-spacing:.5px;color:var(--mute);padding-bottom:12px">CURRENT JOB</div>
          <div style="display:flex;flex-direction:column;gap:8px">
            <span style="font-family:var(--font-mono);font-size:12px;color:var(--body)">{{ store.jobId || '—' }}</span>
            <div><StatusBadge :status="store.status" /></div>
            <span v-if="store.stage" style="font-family:var(--font-mono);font-size:11px;color:var(--mute)">{{ store.stage }}</span>
          </div>
        </div>
      </aside>

      <main style="flex:1;min-width:0;padding:32px 32px 64px;transition:padding .2s ease" :style="mainPad">
        <component :is="page" />
      </main>
    </div>

    <div v-if="store.toasts.length" style="position:fixed;right:24px;bottom:24px;z-index:95;display:flex;flex-direction:column;gap:8px;align-items:flex-end">
      <div v-for="t in store.toasts" :key="t.id"
        style="min-width:280px;max-width:420px;display:flex;align-items:flex-start;gap:10px;background:var(--surface);border-radius:8px;box-shadow:var(--shadow-float);padding:12px 14px;animation:toastIn .22s cubic-bezier(.2,.8,.2,1) both">
        <span :style="{ width: '6px', height: '6px', borderRadius: '50%', background: DOT[t.kind] || DOT.info, marginTop: '7px', flexShrink: 0 }"></span>
        <div style="flex:1;min-width:0;font-size:14px;line-height:20px;color:var(--ink);word-break:break-all">{{ t.text }}</div>
        <button @click="dismissToast(t.id)" style="width:20px;height:20px;padding:0;background:transparent;border:none;color:var(--mute);cursor:pointer;font-size:14px">×</button>
      </div>
    </div>

    <TerminalPanel v-if="store.termPinned || store.termFull" />
    <ModalsHost />
  </div>
</template>
