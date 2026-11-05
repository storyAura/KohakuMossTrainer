<script setup>
// JSON 字典参数编辑器:「表单」逐条加删键值,「JSON」直接写文本;两种模式改的是同一份文本。
// 值按 JSON 字面量解析(1 / 0.95 / true / [1,2]),解析不了就当字符串。
import { computed, ref, watch } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  text: { type: String, default: '' },
  invalid: { type: Boolean, default: false },
})
const emit = defineEmits(['change'])

// 文本 -> 字典;空文本算空字典,不是字典(数字、数组、坏 JSON)返回 null
function parse(text) {
  const t = String(text ?? '').trim()
  if (!t) return {}
  try {
    const v = JSON.parse(t)
    return v && typeof v === 'object' && !Array.isArray(v) ? v : null
  } catch {
    return null
  }
}
const shown = v => typeof v === 'string' ? v : JSON.stringify(v)
function literal(s) {
  try { return JSON.parse(s) } catch { return s }
}
const toRows = obj => Object.entries(obj).map(([k, v]) => ({ k, v: shown(v) }))

const asDict = computed(() => parse(props.text))
const mode = ref(asDict.value ? 'form' : 'json')
const rows = ref(toRows(asDict.value || {}))
let emitted = props.text

// 外部改了文本(恢复预设值、载入预设)时重新铺行;自己刚发出的不算
watch(() => props.text, text => {
  if (text === emitted) return
  emitted = text
  const obj = parse(text)
  if (obj) rows.value = toRows(obj)
  else mode.value = 'json'
})

function send(text) {
  emitted = text
  emit('change', text)
}

function sync() {
  const obj = {}
  for (const r of rows.value) if (r.k.trim()) obj[r.k.trim()] = literal(r.v)
  send(Object.keys(obj).length || String(props.text).trim() ? JSON.stringify(obj) : '')
}

function setRow(i, key, val) {
  rows.value = rows.value.map((r, j) => j === i ? { ...r, [key]: val } : r)
  sync()
}
function addRow() { rows.value = [...rows.value, { k: '', v: '' }] }
function removeRow(i) {
  rows.value = rows.value.filter((_, j) => j !== i)
  sync()
}

function toForm() {
  const obj = asDict.value
  if (!obj) return
  rows.value = toRows(obj)
  mode.value = 'form'
}
</script>

<template>
  <div class="kv">
    <div class="seg kv-mode">
      <button :class="{ on: mode === 'form' }" @click="toForm" :disabled="!asDict"
        :data-tip="asDict ? null : '当前内容不是 {键: 值} 形式,只能用 JSON 编辑'">表单</button>
      <button :class="{ on: mode === 'json' }" @click="mode = 'json'">JSON</button>
    </div>

    <template v-if="mode === 'form'">
      <div v-for="(r, i) in rows" :key="i" class="kv-row">
        <input :value="r.k" @input="setRow(i, 'k', $event.target.value)" class="input mono kv-key" placeholder="参数名" spellcheck="false" />
        <span class="kv-eq">=</span>
        <input :value="r.v" @input="setRow(i, 'v', $event.target.value)" class="input mono" placeholder="值" spellcheck="false" />
        <button class="btn btn-ghost btn-icon" @click="removeRow(i)" data-tip="删除这一条"><Icon name="trash" :size="15" /></button>
      </div>
      <button class="btn kv-add" @click="addRow"><Icon name="plus" :size="15" />添加参数</button>
    </template>

    <textarea v-else :value="text" @input="send($event.target.value)" rows="3" spellcheck="false"
      :class="['input', 'mono', { invalid }]"></textarea>
  </div>
</template>

<style scoped>
.kv { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.kv-mode { align-self: flex-start; }
.kv-mode button { height: 28px; padding: 0 12px; font-size: 13px; }
.kv-row { display: flex; align-items: center; gap: 6px; animation: rowIn var(--t-base) var(--ease) both; }
.kv-key { width: 180px; flex: none; }
.kv-eq { color: var(--faint); font-family: var(--font-mono); }
.kv-add { align-self: flex-start; border-style: dashed; box-shadow: none; background: transparent; }
</style>
