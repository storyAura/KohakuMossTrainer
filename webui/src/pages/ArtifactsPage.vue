<script setup>
// 产物:某个运行目录(或出图目录)下的图片、导出文件与检查点。
import { computed, onMounted, ref } from 'vue'
import { store, toast, loadQueue } from '../store.js'
import { getJson, fileUrl } from '../api.js'

const run = ref('')
const data = ref(null)
const known = computed(() => {
  const dirs = store.queue.map(j => j.run_dir).filter(Boolean)
  const current = (store.form.OUTPUT_DIR || 'runs/moss') + '/' + (store.form.RUN_NAME || 'run')
  return [...new Set([current, ...dirs])]
})

async function load(dir) {
  run.value = dir ?? run.value
  try {
    data.value = await getJson('/api/v1/artifacts?run=' + encodeURIComponent(run.value))
  } catch (err) {
    data.value = null
    toast('error', '读取失败 · ' + err.message)
  }
}

onMounted(() => { load(known.value[0]); loadQueue() })

const size = b => b >= 1 << 30 ? (b / (1 << 30)).toFixed(2) + ' GB' : b >= 1 << 20 ? (b / (1 << 20)).toFixed(1) + ' MB' : Math.round(b / 1024) + ' KB'
const when = t => new Date(t * 1000).toLocaleString()
const card = 'background:var(--surface);border-radius:8px;box-shadow:var(--shadow-card);padding:16px;margin-bottom:24px'
const head = 'font-family:var(--font-mono);font-size:12px;letter-spacing:.5px;color:var(--mute);margin-bottom:12px'
const row = 'display:grid;grid-template-columns:1fr 100px 180px;gap:12px;min-height:36px;align-items:center;border-top:1px solid var(--hairline);font-family:var(--font-mono);font-size:13px'
</script>

<template>
  <div style="animation:pageIn .24s cubic-bezier(.2,.8,.2,1) both;max-width:1280px;margin:0 auto">
    <h1 style="margin:0;font-size:20px;line-height:28px;font-weight:600;color:var(--ink)">产物</h1>
    <p style="margin:4px 0 16px;font-size:14px;line-height:20px;color:var(--body)">训练输出在 &lt;输出目录&gt;/&lt;运行名&gt;/:samples/ 样图、export/ 导出、checkpoints/ 检查点。</p>
    <div style="display:flex;gap:8px;margin-bottom:24px;flex-wrap:wrap">
      <input v-model="run" @keydown.enter="load()" list="known-runs"
        style="flex:1;min-width:280px;height:36px;padding:0 10px;background:var(--surface);border:1px solid var(--hairline);border-radius:6px;font-family:var(--font-mono);font-size:13px;color:var(--ink)" />
      <datalist id="known-runs"><option v-for="k in known" :key="k" :value="k" /></datalist>
      <button @click="load()" class="hv-fade"
        style="height:36px;padding:0 16px;background:var(--primary);color:var(--on-primary);border:none;border-radius:6px;font-size:14px;font-weight:500;cursor:pointer">刷新</button>
    </div>

    <template v-if="data">
      <section :style="card">
        <div :style="head">IMAGES · {{ data.images.length }}</div>
        <div v-if="!data.images.length" style="height:96px;display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:12px;color:var(--mute);border:1px dashed var(--hairline);border-radius:8px">还没有图片</div>
        <div v-else style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px">
          <a v-for="im in data.images" :key="im.path" :href="fileUrl(im.path)" target="_blank" :title="im.path"
            style="display:block;aspect-ratio:1/1;border:1px solid var(--hairline);border-radius:8px;overflow:hidden;background:var(--surface-2)">
            <img :src="fileUrl(im.path)" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block" />
          </a>
        </div>
      </section>
      <section :style="card">
        <div :style="head">EXPORTS · {{ data.exports.length }}</div>
        <div v-if="!data.exports.length" style="font-size:12px;color:var(--mute)">训练结束后导出到 export/</div>
        <div v-for="e in data.exports" :key="e.path" :style="row" :title="e.path">
          <span style="color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ e.name }}</span>
          <span style="color:var(--body);text-align:right">{{ size(e.size) }}</span>
          <span style="color:var(--mute);text-align:right">{{ when(e.mtime) }}</span>
        </div>
      </section>
      <section :style="card">
        <div :style="head">CHECKPOINTS · {{ data.checkpoints.length }}</div>
        <div v-if="!data.checkpoints.length" style="font-size:12px;color:var(--mute)">每 SAVE_EVERY 步保存到 checkpoints/</div>
        <div v-for="c in data.checkpoints" :key="c.path" :style="row" :title="c.path">
          <span style="color:var(--ink)">{{ c.name }}</span><span></span>
          <span style="color:var(--mute);text-align:right">{{ when(c.mtime) }}</span>
        </div>
      </section>
    </template>
  </div>
</template>
