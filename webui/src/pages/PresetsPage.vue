<script setup>
// 预设:保存 / 载入训练表单(configs/user/webui/<名字>.json,提交训练时自动按运行名保存)。
import { onMounted, ref } from 'vue'
import { store, loadPresets, savePreset, applyPreset } from '../store.js'
import Icon from '../components/Icon.vue'

const name = ref('')
onMounted(loadPresets)

function save() {
  const n = (name.value || store.form.RUN_NAME || '').trim()
  if (n) savePreset(n)
}
const when = t => new Date(t * 1000).toLocaleString()
</script>

<template>
  <div class="page" style="max-width:960px">
    <div class="page-head">
      <h1 class="h1">预设</h1>
    </div>
    <div class="save">
      <input v-model="name" :placeholder="store.form.RUN_NAME || '预设名'" @keydown.enter="save" class="input mono" spellcheck="false" />
      <button @click="save" class="btn btn-lg btn-primary" :disabled="!store.env.backend"><Icon name="bookmark" :size="14" />保存当前设置</button>
    </div>
    <section class="card">
      <div v-if="!store.presets.length" class="empty" style="margin:16px"><Icon name="bookmark" :size="18" />还没有预设</div>
      <div v-for="p in store.presets" :key="p.name" class="row">
        <Icon name="bookmark" :size="15" />
        <span class="mono name">{{ p.name }}</span>
        <span class="mono when">{{ when(p.updated) }}</span>
        <button @click="applyPreset(p.name)" class="btn btn-sm btn-soft">载入到训练页</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.save { display: flex; gap: 8px; margin-bottom: 16px; }
.save .input { flex: 1; height: 40px; }
.row { display: flex; align-items: center; gap: 12px; padding: 0 16px; min-height: 54px; border-top: 1px solid var(--hairline-soft); color: var(--mute); transition: background var(--t-snap) var(--ease); }
.row:first-child { border-top: none; }
.row:hover { background: var(--surface-3); }
.name { flex: 1; font-size: 14px; color: var(--ink); }
.when { font-size: 13px; color: var(--faint); }
</style>
