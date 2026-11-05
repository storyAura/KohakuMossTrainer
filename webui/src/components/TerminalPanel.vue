<script setup>
// 作业原样日志终端:自动吸底、回到底部浮钮、双击全屏(Esc 退出)、
// 「置顶」后变成跨页面常驻的悬浮控制台(横排贴底 / 竖排靠右,透明度可调)。
// 同一组件同时服务训练页停靠形态与全局悬浮形态,形态由 store 的 termPinned/termFull 决定。
import { computed, nextTick, ref, watch } from 'vue'
import {
  store, onLogScroll, termDbl, togglePin, toggleOrient, setTermOp,
  copyLogs, clearLogs, toggleScroll,
} from '../store.js'
import Icon from './Icon.vue'

const bodyEl = ref(null)

const KIND_COLOR = { ink: '#e2e8f0', dim: '#94a3b8', warn: '#fcd34d', err: '#fda4af' }

const floatingCtl = computed(() => store.termPinned && !store.termFull)
const termOpPct = computed(() => Math.round(store.termOp * 100))

const wrapStyle = computed(() => {
  if (store.termFull) return { position: 'fixed', inset: '0', zIndex: 90, borderRadius: '0' }
  if (!store.termPinned) return {}
  // 透明度完全由滑杆控制(不做 hover 强制不透明——那会让拖动滑杆时看不到实时效果)
  const base = { position: 'fixed', zIndex: 65, boxShadow: 'var(--shadow-modal)', opacity: store.termOp }
  return store.termOrient === 'h'
    ? { ...base, left: '92px', right: '16px', bottom: '16px', height: '236px' }
    : { ...base, top: '72px', right: '16px', bottom: '16px', width: '440px' }
})

const bodyHeight = computed(() => {
  if (store.termFull || (store.termPinned && store.termOrient === 'v')) return '100%'
  return store.termPinned ? '188px' : '280px'
})

function scrollToBottom() {
  if (bodyEl.value) bodyEl.value.scrollTop = bodyEl.value.scrollHeight
}

function jumpBottom() {
  store.autoScroll = true
  store.atBottom = true
  scrollToBottom()
}

watch(() => [store.logs.length, store.autoScroll], async () => {
  if (!store.autoScroll) return
  await nextTick()
  scrollToBottom()
})
</script>

<template>
  <section class="term" :style="wrapStyle">
    <div class="term-bar">
      <span class="eyebrow">终端</span>
      <span class="term-hint">{{ store.termFull ? '双击或 Esc 退出全屏' : '双击日志全屏' }}</span>
      <span style="flex:1"></span>
      <template v-if="floatingCtl">
        <input type="range" min="35" max="100" :value="termOpPct" @input="setTermOp" class="op" aria-label="透明度" />
        <button @click="toggleOrient" class="btn btn-ghost btn-sm btn-icon" :data-tip="store.termOrient === 'h' ? '改成竖排(靠右)' : '改成横排(贴底)'">
          <Icon :name="store.termOrient === 'h' ? 'columns' : 'rows'" :size="14" />
        </button>
      </template>
      <button @click="toggleScroll" :class="['btn', 'btn-ghost', 'btn-sm', 'btn-icon', { active: store.autoScroll }]"
        :data-tip="store.autoScroll ? '自动滚动:开' : '自动滚动:关'">
        <Icon name="arrowDown" :size="14" />
      </button>
      <button @click="copyLogs" class="btn btn-ghost btn-sm btn-icon" data-tip="复制全部日志"><Icon name="copy" :size="14" /></button>
      <button @click="clearLogs" class="btn btn-ghost btn-sm btn-icon" data-tip="清空"><Icon name="trash" :size="14" /></button>
      <button @click="termDbl" class="btn btn-ghost btn-sm btn-icon" :data-tip="store.termFull ? '退出全屏' : '全屏'"><Icon name="expand" :size="14" /></button>
      <button @click="togglePin" :class="['btn', 'btn-ghost', 'btn-sm', 'btn-icon', { active: store.termPinned }]"
        :data-tip="store.termPinned ? '收回到训练页' : '置顶(切换页面也能看到)'">
        <Icon name="pin" :size="14" />
      </button>
    </div>
    <div class="term-wrap">
      <div ref="bodyEl" @scroll="onLogScroll" @dblclick="termDbl" class="term-body" :style="{ height: bodyHeight }">
        <div v-if="!store.logs.length" class="term-empty">暂无日志</div>
        <div v-for="l in store.logs" :key="l.id" class="line" :style="{ color: KIND_COLOR[l.kind] || KIND_COLOR.ink }">{{ l.text }}</div>
      </div>
      <button v-if="!store.atBottom" @click="jumpBottom" class="btn btn-sm to-bottom">
        <Icon name="arrowDown" :size="13" />回到底部
      </button>
    </div>
  </section>
</template>

<style scoped>
.term { display: flex; flex-direction: column; overflow: hidden; background: var(--surface); border: 1px solid var(--hairline); border-radius: var(--r-lg); transition: opacity var(--t-snap) var(--ease); }
.term-bar { display: flex; align-items: center; gap: 2px; padding: 6px 8px 6px 14px; background: var(--surface); border-bottom: 1px solid var(--hairline); }
.term-hint { margin-left: 8px; font-size: 13.5px; color: var(--faint); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.op { width: 64px; margin-right: 4px; accent-color: var(--primary); }
.active { color: var(--primary); }
.term-wrap { position: relative; flex: 1 1 auto; min-height: 0; }
.term-body { overflow-y: auto; overflow-x: hidden; background: var(--terminal-bg); padding: 10px 14px; }
.term-empty { font-family: var(--font-mono); font-size: 13px; color: #64748b; }
.line { font-family: var(--font-mono); font-size: 13.5px; line-height: 21px; white-space: pre-wrap; word-break: break-all; animation: lineIn var(--t-snap) ease-out both; }
.to-bottom { position: absolute; right: 12px; bottom: 12px; box-shadow: var(--shadow-float); animation: toastIn var(--t-snap) var(--ease) both; }
</style>
