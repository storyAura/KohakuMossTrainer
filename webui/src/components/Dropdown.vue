<script setup>
// 下拉框:替代原生 select / datalist。列表挂到 body 上(不被卡片的 overflow 裁掉),
// 键盘 ↑↓ 选择、Enter 确认、Esc 关闭;空间不够时向上展开。
// editable = 可输入的组合框(输入时按文字过滤候选,Enter 抛出 enter 事件)。
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] },
  mono: { type: Boolean, default: true },
  editable: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
  placeholder: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'enter'])

const LIST_MAX = 300
const GAP = 4
const root = ref(null)
const list = ref(null)
const open = ref(false)
const active = ref(-1)
const filter = ref('')
// 组合框里用 ↑↓ 挑过候选后,Enter 选中它;否则 Enter 提交输入的文字
const navigated = ref(false)
const pos = ref({})

const current = computed(() => props.options.find(o => String(o.v) === String(props.modelValue)))
const shown = computed(() => {
  const q = filter.value.trim().toLowerCase()
  if (!props.editable || !q) return props.options
  return props.options.filter(o => String(o.label || o.v).toLowerCase().includes(q))
})
const labelOf = o => (o.label ?? o.v) === '' ? '(空)' : (o.label ?? o.v)

function place() {
  const r = root.value?.getBoundingClientRect()
  if (!r) return
  const below = window.innerHeight - r.bottom
  const up = below < Math.min(LIST_MAX, shown.value.length * 38 + 12) + GAP && r.top > below
  pos.value = {
    left: r.left + 'px', minWidth: r.width + 'px', maxWidth: Math.max(r.width, 520) + 'px',
    ...(up ? { bottom: (window.innerHeight - r.top + GAP) + 'px' } : { top: (r.bottom + GAP) + 'px' }),
  }
}

async function show() {
  if (open.value) return
  filter.value = ''
  navigated.value = false
  active.value = Math.max(0, shown.value.indexOf(current.value))
  open.value = true
  place()
  await nextTick()
  list.value?.children[active.value]?.scrollIntoView({ block: 'nearest' })
}

function hide() { open.value = false }
function toggle() { open.value ? hide() : show() }

function pick(o) {
  emit('update:modelValue', o.v)
  hide()
  if (props.editable) emit('enter')
}

function move(d) {
  if (!open.value) {
    show()
    navigated.value = true
    return
  }
  navigated.value = true
  const n = shown.value.length
  if (!n) return
  active.value = (active.value + d + n) % n
  nextTick(() => list.value?.children[active.value]?.scrollIntoView({ block: 'nearest' }))
}

function onKey(e) {
  switch (e.key) {
    case 'ArrowDown': e.preventDefault(); move(1); break
    case 'ArrowUp': e.preventDefault(); move(-1); break
    case 'Enter':
      e.preventDefault()
      if (open.value && shown.value[active.value] && (!props.editable || filter.value || navigated.value)) pick(shown.value[active.value])
      else if (props.editable) { hide(); emit('enter') } else show()
      break
    case 'Escape': if (open.value) { e.stopPropagation(); hide() } break
    case 'Tab': hide(); break
  }
}

function onType(e) {
  filter.value = e.target.value
  emit('update:modelValue', e.target.value)
  if (!open.value) show()
  active.value = 0
}

// 点外面、窗口缩放、页面滚动(列表自身滚动除外)都收起
function onOutside(e) {
  if (!root.value?.contains(e.target) && !list.value?.contains(e.target)) hide()
}
function onScroll(e) { if (!list.value?.contains(e.target)) hide() }

watch(open, on => {
  const fn = on ? 'addEventListener' : 'removeEventListener'
  document[fn]('mousedown', onOutside, true)
  window[fn]('scroll', onScroll, true)
  window[fn]('resize', hide)
})
onBeforeUnmount(() => { open.value = false })
</script>

<template>
  <div ref="root" :class="['dd', { open, invalid, editable }]">
    <template v-if="editable">
      <input :value="modelValue" @input="onType" @keydown="onKey" @focus="filter = ''" :placeholder="placeholder"
        :class="['input', { mono }]" spellcheck="false" />
      <button type="button" class="dd-caret-btn" tabindex="-1" @click="toggle" aria-label="展开候选">
        <Icon name="chevron" :size="15" />
      </button>
    </template>
    <button v-else type="button" :class="['input', 'dd-trigger', { mono }]" @click="toggle" @keydown="onKey"
      :aria-expanded="open" aria-haspopup="listbox">
      <span :class="['dd-value', { placeholder: !current }]">{{ current ? labelOf(current) : (modelValue || placeholder || '请选择') }}</span>
      <span class="dd-caret"><Icon name="chevron" :size="15" /></span>
    </button>
    <Teleport to="body">
      <ul v-if="open && shown.length" ref="list" class="dd-list" :style="pos" role="listbox">
        <li v-for="(o, i) in shown" :key="String(o.v)" role="option" :aria-selected="o === current"
          :class="['dd-item', { active: i === active, selected: o === current, mono }]"
          @mousedown.prevent="pick(o)" @mousemove="active = i">
          <span class="dd-label">{{ labelOf(o) }}</span>
          <span v-if="o.hint" class="dd-hint">{{ o.hint }}</span>
          <span class="dd-check"><Icon v-if="o === current" name="check" :size="15" /></span>
        </li>
      </ul>
    </Teleport>
  </div>
</template>

<style>
.dd { position: relative; display: inline-flex; min-width: 220px; }
.dd.editable { display: flex; min-width: 0; }
.dd-trigger { display: flex; align-items: center; justify-content: space-between; gap: 8px; cursor: pointer; text-align: left; }
.dd.open .dd-trigger, .dd.open .input { border-color: var(--primary); box-shadow: 0 0 0 3px var(--focus-ring); }
.dd.invalid .input { border-color: var(--error); }
.dd-value { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dd-value.placeholder { color: var(--faint); }
.dd-caret { display: inline-flex; color: var(--faint); transition: transform var(--t-base) var(--ease); }
.dd.open .dd-caret { transform: rotate(180deg); color: var(--primary); }
.dd.editable .input { padding-right: 38px; }
.dd-caret-btn {
  position: absolute; right: 4px; top: 50%; transform: translateY(-50%); width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center; border: none; border-radius: var(--r-sm);
  background: transparent; color: var(--faint); cursor: pointer;
}
.dd-caret-btn:hover { background: var(--surface-2); color: var(--ink); }
.dd-list {
  position: fixed; z-index: 140; margin: 0; padding: 4px; list-style: none; max-height: 300px; overflow-y: auto;
  background: var(--surface); border: 1px solid var(--hairline); border-radius: 10px; box-shadow: var(--shadow-float);
  animation: ddIn var(--t-snap) var(--ease) both;
}
.dd-item {
  display: flex; align-items: center; gap: 10px; min-height: 36px; padding: 0 10px; border-radius: var(--r-sm);
  font-size: 14px; color: var(--body); cursor: pointer;
}
.dd-item.mono { font-family: var(--font-mono); font-size: 13.5px; }
.dd-item.active { background: var(--surface-2); color: var(--ink); }
.dd-item.selected { color: var(--primary); font-weight: 600; }
.dd-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dd-hint { font-size: 12px; color: var(--faint); white-space: nowrap; }
.dd-check { width: 15px; display: inline-flex; }
@keyframes ddIn { from { opacity: 0; transform: translateY(-3px); } to { opacity: 1; transform: none; } }
</style>
