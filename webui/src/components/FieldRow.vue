<script setup>
// 单个参数行:中文 label + mono 旋钮名(说明悬停 ⓘ 查看)+ 按类型渲染的控件;改过的字段左侧琥珀标记、
// 可一键恢复预设值;后端校验问题显示在控件下方。
import Dropdown from './Dropdown.vue'
import Icon from './Icon.vue'
import KvEditor from './KvEditor.vue'

defineProps({ f: { type: Object, required: true } })
</script>

<template>
  <div :class="['row', { dirty: f.dirty, bad: f.error }]">
    <div class="label">
      <div class="label-top">
        <span class="name">{{ f.label }}</span>
        <span v-if="f.hint" class="info" :data-tip="f.hint" data-tip-wrap><Icon name="info" :size="14" /></span>
        <span v-if="f.dirty" class="chip chip-warning changed">已改</span>
      </div>
      <div class="flag mono">{{ f.flag }}</div>
    </div>
    <div class="control">
      <div class="control-line">
        <Dropdown v-if="f.isCombo" editable :model-value="f.value" :options="f.options" :invalid="!!f.error"
          :placeholder="f.ph" @update:model-value="f.onPick" class="combo" />

        <input v-else-if="f.isPath" :value="f.value" @input="f.onInput" :placeholder="f.ph" spellcheck="false"
          :class="['input', 'mono', { invalid: f.error }]" />

        <input v-else-if="f.isText" :value="f.value" @input="f.onInput" :placeholder="f.ph" spellcheck="false"
          :class="['input', { invalid: f.error }]" style="max-width:320px" />

        <input v-else-if="f.isNum" :value="f.value" @input="f.onInput" inputmode="decimal" spellcheck="false"
          :class="['input', 'mono', { invalid: f.error }]" style="width:160px;text-align:right" />

        <Dropdown v-else-if="f.isSelect" :model-value="f.value" :options="f.options" :invalid="!!f.error"
          @update:model-value="f.onPick" />

        <div v-else-if="f.isSeg" class="seg">
          <button v-for="o in f.segs" :key="o.label" :class="{ on: o.active }" @click="o.go">{{ o.label }}</button>
        </div>

        <KvEditor v-else-if="f.isJson" :text="String(f.value ?? '')" :invalid="!!f.error" @change="f.onPick" />

        <textarea v-else-if="f.isArea" :value="f.value" @input="f.onInput" rows="3" :placeholder="f.ph" spellcheck="false"
          :class="['input', 'mono', { invalid: f.error }]"></textarea>

        <button v-else-if="f.isOn || f.isOff" :class="['switch', { on: f.isOn }]" @click="f.onToggle"
          role="switch" :aria-checked="f.isOn" :aria-label="f.label"></button>

        <button v-if="f.dirty && f.onReset" class="btn btn-ghost btn-sm btn-icon reset" @click="f.onReset"
          :data-tip="'恢复预设值:' + (f.preset === '' ? '(空)' : f.preset)">
          <Icon name="reset" :size="14" />
        </button>
      </div>
      <div v-if="f.error" class="error"><Icon name="alert" :size="13" />{{ f.error }}</div>
    </div>
  </div>
</template>

<style scoped>
.row {
  display: grid; grid-template-columns: 236px minmax(0, 1fr); gap: 18px; align-items: start;
  margin: 0 -12px; padding: 10px 12px; border-left: 2px solid transparent; border-radius: 0 var(--r-sm) var(--r-sm) 0;
  transition: background var(--t-snap) var(--ease), border-color var(--t-snap) var(--ease);
}
.row.dirty { border-left-color: var(--warning); background: var(--warning-soft); }
.row.bad { border-left-color: var(--error); background: var(--error-soft); }
.label { padding-top: 7px; min-width: 0; }
.label-top { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.name { font-size: 14.5px; line-height: 22px; font-weight: 500; color: var(--ink); }
.changed { height: 20px; padding: 0 7px; font-size: 11px; }
.flag { font-size: 12px; line-height: 18px; color: var(--faint); word-break: break-all; }
.info { display: inline-flex; color: var(--faint); cursor: help; }
.info:hover { color: var(--primary); }
.combo { flex: 1; }
.control { min-width: 0; }
.control-line { display: flex; align-items: flex-start; gap: 6px; min-height: 38px; }
.control-line > .input:not([style]) { flex: 1; }
.control-line > .switch { margin-top: 7px; }
.control-line > .reset { margin-top: 3px; }
.reset { color: var(--warning-ink); }
.error { display: flex; align-items: flex-start; gap: 5px; margin-top: 6px; font-size: 13px; line-height: 19px; color: var(--error-ink); animation: rowIn var(--t-snap) var(--ease) both; }
.error svg { margin-top: 2px; }
@media (max-width: 720px) { .row { grid-template-columns: 1fr; gap: 6px; } }
</style>
