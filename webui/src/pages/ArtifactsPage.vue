<script setup>
// 产物:某个运行目录(或出图目录)下的图片、导出文件与检查点。
import { computed, onMounted, ref } from 'vue'
import { store, toast, loadQueue } from '../store.js'
import { getJson, fileUrl } from '../api.js'
import Dropdown from '../components/Dropdown.vue'
import Icon from '../components/Icon.vue'

const run = ref('')
const data = ref(null)
const loading = ref(false)
const known = computed(() => {
  const dirs = store.queue.map(j => j.run_dir).filter(Boolean)
  const current = (store.form.OUTPUT_DIR || 'runs/moss') + '/' + (store.form.RUN_NAME || 'run')
  return [...new Set([current, ...store.runs.map(r => r.run), ...dirs])]
})

async function load(dir) {
  run.value = dir ?? run.value
  loading.value = true
  try {
    data.value = await getJson('/api/v1/artifacts?run=' + encodeURIComponent(run.value))
  } catch (err) {
    data.value = null
    toast('error', '读取失败 · ' + err.message)
  } finally {
    loading.value = false
  }
}

onMounted(() => { load(known.value[0]); loadQueue() })

function copyPath(path) {
  navigator.clipboard?.writeText(path)
  toast('info', '路径已复制')
}

const size = b => b >= 1 << 30 ? (b / (1 << 30)).toFixed(2) + ' GB' : b >= 1 << 20 ? (b / (1 << 20)).toFixed(1) + ' MB' : Math.round(b / 1024) + ' KB'
const when = t => new Date(t * 1000).toLocaleString()
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1 class="h1">产物</h1>
    </div>
    <div class="picker">
      <Dropdown v-model="run" editable :options="known.map(k => ({ v: k }))" @enter="load()"
        placeholder="运行目录,如 runs/moss/my-lora" class="picker-dd" />
      <button @click="load()" class="btn btn-lg btn-primary" :disabled="loading"><Icon name="refresh" :size="14" />{{ loading ? '读取中…' : '读取' }}</button>
    </div>
    <div v-if="known.length > 1" class="recent">
      <span class="eyebrow">最近</span>
      <button v-for="k in known" :key="k" @click="load(k)" :class="['chip', k === run ? 'chip-primary' : '']">{{ k }}</button>
    </div>

    <template v-if="data">
      <section class="card card-pad block">
        <div class="card-head"><span class="eyebrow">图片</span><span class="chip chip-neutral">{{ data.images.length }}</span></div>
        <div v-if="!data.images.length" class="empty" style="margin-top:12px"><Icon name="image" :size="18" />还没有图片</div>
        <div v-else class="gallery">
          <a v-for="im in data.images" :key="im.path" :href="fileUrl(im.path)" target="_blank" :title="im.path" class="thumb">
            <img :src="fileUrl(im.path)" loading="lazy" alt="" />
          </a>
        </div>
      </section>
      <section class="card card-pad block">
        <div class="card-head"><span class="eyebrow">导出</span><span class="chip chip-neutral">{{ data.exports.length }}</span></div>
        <div v-if="!data.exports.length" class="empty" style="margin-top:12px">还没有导出</div>
        <div v-for="e in data.exports" :key="e.path" class="file" :title="e.path">
          <Icon name="box" :size="15" />
          <span class="mono name">{{ e.name }}</span>
          <span class="mono muted">{{ size(e.size) }}</span>
          <span class="mono faint">{{ when(e.mtime) }}</span>
          <button class="btn btn-ghost btn-sm btn-icon" @click="copyPath(e.path)" data-tip="复制路径" data-tip-side="left"><Icon name="copy" :size="13" /></button>
        </div>
      </section>
      <section class="card card-pad block">
        <div class="card-head"><span class="eyebrow">检查点</span><span class="chip chip-neutral">{{ data.checkpoints.length }}</span></div>
        <div v-if="!data.checkpoints.length" class="empty" style="margin-top:12px">还没有检查点</div>
        <div v-for="c in data.checkpoints" :key="c.path" class="file" :title="c.path">
          <Icon name="folder" :size="15" />
          <span class="mono name">{{ c.name }}</span>
          <span></span>
          <span class="mono faint">{{ when(c.mtime) }}</span>
          <button class="btn btn-ghost btn-sm btn-icon" @click="copyPath(c.path)" data-tip="复制路径" data-tip-side="left"><Icon name="copy" :size="13" /></button>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.picker { display: flex; gap: 8px; margin-bottom: 10px; }
.picker-dd { flex: 1; }
.picker-dd .input { height: 40px; }
.recent { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 18px; }
.block { margin-bottom: 14px; }
.gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr)); gap: 10px; margin-top: 12px; }
.thumb { display: block; aspect-ratio: 1 / 1; border: 1px solid var(--hairline); border-radius: var(--r-md); overflow: hidden; background: var(--surface-2); }
.thumb img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform var(--t-base) var(--ease); }
.thumb:hover img { transform: scale(1.03); }
.file { display: grid; grid-template-columns: 16px minmax(0, 1fr) 90px 180px 32px; gap: 10px; align-items: center; min-height: 44px; border-top: 1px solid var(--hairline-soft); font-size: 13.5px; color: var(--mute); }
.card-head + .file { margin-top: 10px; }
.name { color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.faint { color: var(--faint); text-align: right; }
.muted { text-align: right; }
</style>
