<script setup>
// 应用壳:左侧图标导航栏(主题切换、后端状态)、顶栏(运行概要 / GPU / 联机状态 / 开始与停止)、
// 页面切换、提示条、置顶悬浮终端(跨页面常驻)、弹窗宿主。
import { computed, onMounted, onUnmounted } from 'vue'
import { store, init, destroy, cycleTheme, startRun, askCancel, dismissToast } from './store.js'
import Icon from './components/Icon.vue'
import StatusBadge from './components/StatusBadge.vue'
import TerminalPanel from './components/TerminalPanel.vue'
import ModalsHost from './components/ModalsHost.vue'
import TrainPage from './pages/TrainPage.vue'
import ToolsPage from './pages/ToolsPage.vue'
import QueuePage from './pages/QueuePage.vue'
import ArtifactsPage from './pages/ArtifactsPage.vue'
import ModelsPage from './pages/ModelsPage.vue'
import PresetsPage from './pages/PresetsPage.vue'
import EnvironmentPage from './pages/EnvironmentPage.vue'

onMounted(init)
onUnmounted(destroy)

const PAGES = {
  train: ['训练', 'train', TrainPage], tools: ['出图', 'image', ToolsPage], queue: ['队列', 'queue', QueuePage],
  artifacts: ['产物', 'folder', ArtifactsPage], models: ['模型', 'box', ModelsPage],
  presets: ['预设', 'bookmark', PresetsPage], env: ['环境', 'cpu', EnvironmentPage],
}
const nav = computed(() => Object.entries(PAGES).map(([key, [label, icon]]) => ({ key, label, icon, active: store.page === key })))
const current = computed(() => PAGES[store.page] || PAGES.train)

const busy = computed(() => ['queued', 'running', 'cancelling'].includes(store.status))
const gpu = computed(() => {
  const g = store.env.gpus?.[0]
  if (!g) return null
  const used = g.memory_used_mb / 1024, total = g.memory_total_mb / 1024
  const name = g.name.replace(/NVIDIA\s*/i, '').replace(/GeForce\s*/i, '')
  return { label: name + ' · ' + used.toFixed(1) + '/' + total.toFixed(1) + ' GB', warn: used / total > 0.92 }
})
const runName = computed(() => store.form.RUN_NAME || 'run')
const runLayers = computed(() => [store.layers.algo, store.layers.vram, store.layers.precision].join(' · '))
const THEME = { system: ['monitor', '跟随系统'], light: ['sun', '浅色'], dark: ['moon', '深色'] }
const theme = computed(() => THEME[store.themePref] || THEME.system)
const mainPad = computed(() => {
  if (!store.termPinned || store.termFull) return {}
  return store.termOrient === 'v' ? { paddingRight: '472px' } : { paddingBottom: '268px' }
})
const TOAST_ICON = { error: 'alert', warn: 'alert', info: 'checkCircle' }
</script>

<template>
  <div class="shell">
    <nav class="rail">
      <div class="rail-nav">
        <button v-for="n in nav" :key="n.key" @click="store.page = n.key" :class="['rail-item', { on: n.active }]">
          <Icon :name="n.icon" :size="21" />
          <span>{{ n.label }}</span>
        </button>
      </div>
      <div class="rail-foot">
        <button class="btn btn-ghost btn-icon" @click="cycleTheme" :data-tip="'主题:' + theme[1] + '(点击切换)'" data-tip-side="right">
          <Icon :name="theme[0]" :size="19" />
        </button>
      </div>
    </nav>

    <div class="column">
      <header class="topbar">
        <div class="topbar-left">
          <span class="page-dot" :style="{ color: busy ? 'var(--primary)' : 'var(--warning)' }"><span class="dot" :class="{ live: busy }"></span></span>
          <span class="page-name">{{ current[0] }}</span>
          <span class="chip chip-warning" data-tip="运行名(输出子目录与配置文件名)">{{ runName }}</span>
          <span class="chip chip-neutral topbar-layers" data-tip="算法 · 显存档位 · 精度">{{ runLayers }}</span>
        </div>
        <div class="topbar-right">
          <span v-if="gpu" :class="['chip', gpu.warn ? 'chip-warning' : 'chip-neutral', 'topbar-gpu']" data-tip="显卡 0 · 显存占用">{{ gpu.label }}</span>
          <span v-if="store.env.backend" class="chip chip-success"><span class="dot"></span>已联机</span>
          <span v-else class="chip chip-warning" data-tip="在终端运行 kohakumoss-webui"><span class="dot live"></span>未联机</span>
          <StatusBadge v-if="store.status !== 'idle'" :status="store.status" />
          <button v-if="busy" @click="askCancel" class="btn btn-danger">
            <Icon name="stop" :size="14" />停止
          </button>
          <button @click="startRun" class="btn btn-success" :disabled="!store.env.backend"
            :data-tip="busy ? '排在当前作业之后 · Ctrl+Enter' : 'Ctrl+Enter'">
            <Icon name="play" :size="14" />{{ busy ? '加入队列' : '开始训练' }}
          </button>
        </div>
      </header>

      <main class="main" :style="mainPad">
        <component :is="current[2]" />
      </main>
    </div>

    <div v-if="store.toasts.length" class="toasts">
      <div v-for="t in store.toasts" :key="t.id" :class="['toast', t.kind]">
        <Icon :name="TOAST_ICON[t.kind] || 'checkCircle'" :size="15" />
        <div class="toast-text">{{ t.text }}</div>
        <button @click="dismissToast(t.id)" class="toast-x" aria-label="关闭"><Icon name="x" :size="13" /></button>
      </div>
    </div>

    <TerminalPanel v-if="store.termPinned || store.termFull" />
    <ModalsHost />
  </div>
</template>

<style scoped>
.shell { min-height: 100vh; display: flex; background: var(--canvas); }
.rail {
  position: sticky; top: 0; height: 100vh; flex: 0 0 76px; display: flex; flex-direction: column; align-items: center;
  gap: 14px; padding: 14px 0; background: var(--rail); border-right: 1px solid var(--hairline); z-index: 50;
}
.rail-nav { display: flex; flex-direction: column; gap: 6px; width: 100%; padding: 0 9px; }
.rail-item {
  height: 58px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
  border: 1px solid transparent; border-radius: var(--r-md); background: transparent; color: var(--mute);
  font-size: 12.5px; cursor: pointer; transition: background var(--t-snap) var(--ease), color var(--t-snap) var(--ease);
}
.rail-item:hover { background: var(--surface); color: var(--ink); }
.rail-item.on { background: var(--surface); border-color: var(--hairline); color: var(--primary); box-shadow: var(--shadow-xs); font-weight: 600; }
.rail-foot { margin-top: auto; }
.column { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.topbar {
  position: sticky; top: 0; z-index: 40; height: 56px; display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 0 20px; background: var(--surface); border-bottom: 1px solid var(--hairline);
}
.topbar-left, .topbar-right { display: flex; align-items: center; gap: 10px; min-width: 0; }
.page-dot { display: inline-flex; }
.page-name { font-size: 16px; font-weight: 600; color: var(--ink); margin-right: 4px; white-space: nowrap; }
.main { flex: 1; min-width: 0; padding: 24px 24px 64px; transition: padding var(--t-base) var(--ease); }
.toasts { position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%); z-index: 130; display: flex; flex-direction: column; gap: 8px; align-items: center; }
.toast {
  min-width: 280px; max-width: 560px; display: flex; align-items: flex-start; gap: 10px; padding: 12px 14px;
  background: var(--toast-bg); color: #fff; border-radius: 10px; box-shadow: 0 8px 24px rgba(15, 23, 42, .25);
  font-size: 14px; line-height: 20px; animation: toastIn var(--t-base) var(--ease) both;
}
.toast > svg { margin-top: 1px; color: #6ee7b7; }
.toast.error > svg { color: #fda4af; }
.toast.warn > svg { color: #fcd34d; }
.toast-text { flex: 1; min-width: 0; word-break: break-all; }
.toast-x { background: none; border: none; padding: 2px; color: rgba(255, 255, 255, .6); cursor: pointer; }
.toast-x:hover { color: #fff; }
@media (max-width: 1100px) { .topbar-layers, .topbar-gpu { display: none; } }
</style>
