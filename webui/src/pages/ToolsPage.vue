<script setup>
// 工具页:用训练成果出图(scripts/sample/sample.py)与导出适配器(scripts/export/export.py)。
import { computed, reactive } from 'vue'
import { store, submitJob, toast } from '../store.js'
import { getJson } from '../api.js'
import FieldRow from '../components/FieldRow.vue'
import Icon from '../components/Icon.vue'

const sample = reactive({
  precision: 'bf16', WEIGHTS: '', ADAPTERS: '', PROMPTS: '', NEGATIVE: '',
  H: '1024', W: '1024', STEPS: '50', CFG: '3.0', SEED_BASE: '0', OUT: 'runs/samples', MEMORY_PROFILE: '',
})
const exp = reactive({
  WEIGHTS: '', ADAPTER: '', OUT: '', FORMAT: 'comfy', STYLE: 'lora_unet', SAVE_DTYPE: 'bf16', MULTIPLIER: '1.0',
})

const opt = vs => vs.map(v => ({ v, label: v || '默认(常驻)' }))

function mk(model, label, key, type, extra = {}) {
  const v = model[key]
  return {
    label, flag: extra.flag ?? key, hint: extra.hint || '', ph: extra.ph || '', value: v, error: '',
    options: extra.options || [],
    isCombo: type === 'combo', isPath: type === 'path', isText: type === 'text', isNum: type === 'num', isSelect: type === 'select',
    isArea: type === 'area', isSeg: false, segs: [], isOn: false, isOff: false,
    onInput: ev => { model[key] = ev.target.value }, onPick: v => { model[key] = v }, onToggle: () => {},
  }
}

const weightOptions = computed(() => store.weightDirs.map(w => ({ v: w.path, hint: w.kind === 'hf' ? 'HF' : 'ComfyUI' })))

const sampleFields = computed(() => [
  mk(sample, '模型权重', 'WEIGHTS', 'combo', { ph: store.form.WEIGHTS || 'models/MOSS-Image-Base', options: weightOptions.value }),
  mk(sample, '适配器', 'ADAPTERS', 'area', { hint: '每行一个,路径:强度', ph: 'runs/moss/my-lora/export/my-lora-comfy.safetensors:1.0' }),
  mk(sample, '提示词', 'PROMPTS', 'area', { hint: '每行一条,一条出一张' }),
  mk(sample, '负面提示词', 'NEGATIVE', 'area'),
  mk(sample, '高', 'H', 'num', { flag: 'SIZES' }),
  mk(sample, '宽', 'W', 'num', { flag: 'SIZES' }),
  mk(sample, '步数', 'STEPS', 'num'),
  mk(sample, 'CFG', 'CFG', 'num'),
  mk(sample, '种子', 'SEED_BASE', 'num'),
  mk(sample, '输出目录', 'OUT', 'path'),
  mk(sample, '精度', 'precision', 'select', { flag: 'configs/sample/precision', options: opt(store.caps.sample_precision || ['bf16', 'fp16']) }),
  mk(sample, '显存方案', 'MEMORY_PROFILE', 'select', { options: opt(['', ...store.caps.profiles]) }),
])

const exportFields = computed(() => [
  mk(exp, '模型权重', 'WEIGHTS', 'combo', { ph: store.form.WEIGHTS || 'models/MOSS-Image-Base', options: weightOptions.value }),
  mk(exp, '训练状态', 'ADAPTER', 'path', { hint: '检查点里的 trainable.safetensors' }),
  mk(exp, '输出文件', 'OUT', 'path', { ph: 'lora.safetensors' }),
  mk(exp, '格式', 'FORMAT', 'select', { options: opt(['comfy', 'lycoris', 'merged', 'diffusers']) }),
  mk(exp, '键名风格', 'STYLE', 'select', { options: opt(['lora_unet', 'diffusion_model']) }),
  mk(exp, '保存精度', 'SAVE_DTYPE', 'select', { options: opt(['bf16', 'fp16', 'fp32']) }),
  mk(exp, '合并强度', 'MULTIPLIER', 'num', { hint: '仅 merged' }),
])

const runDir = () => (store.form.OUTPUT_DIR || 'runs/moss') + '/' + (store.form.RUN_NAME || 'run')

async function latest() {
  try {
    return await getJson('/api/v1/artifacts?run=' + encodeURIComponent(runDir()))
  } catch (err) {
    toast('error', '读取产物失败 · ' + err.message)
    return null
  }
}

async function useLatestExport() {
  const r = await latest()
  const pick = r?.exports.find(e => e.name.endsWith('-comfy.safetensors')) || r?.exports.find(e => e.name.endsWith('.safetensors'))
  if (!pick) return toast('warn', '还没有导出文件 · ' + runDir() + '/export/')
  sample.ADAPTERS = pick.path + ':1.0'
  toast('info', '已填入 · ' + pick.name)
}

async function useLatestCheckpoint() {
  const r = await latest()
  if (!r?.checkpoints.length) return toast('warn', '还没有检查点 · ' + runDir() + '/checkpoints/')
  exp.ADAPTER = r.checkpoints[0].path + '/trainable.safetensors'
  toast('info', '已填入 · ' + r.checkpoints[0].name)
}

const lines = text => text.split('\n').map(s => s.trim()).filter(Boolean)
const weights = w => w || store.form.WEIGHTS || 'models/MOSS-Image-Base'

function runSample() {
  if (!lines(sample.PROMPTS).length) return toast('warn', '先写至少一条提示词')
  submitJob('/api/v1/jobs/sample', {
    precision: sample.precision,
    knobs: {
      WEIGHTS: weights(sample.WEIGHTS), ADAPTERS: lines(sample.ADAPTERS), PROMPT: '', PROMPTS: lines(sample.PROMPTS),
      NEGATIVE: sample.NEGATIVE, SIZES: [[sample.H, sample.W]], STEPS: sample.STEPS, CFG: sample.CFG,
      SEED_BASE: sample.SEED_BASE, OUT: sample.OUT, MEMORY_PROFILE: sample.MEMORY_PROFILE,
    },
  }, '出图')
}

function runExport() {
  submitJob('/api/v1/jobs/export', { knobs: { ...exp, WEIGHTS: weights(exp.WEIGHTS) } }, '导出')
}

</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1 class="h1">出图与导出</h1>
    </div>
    <div class="cols">
      <section class="card card-pad" style="flex:1 1 560px;min-width:0">
        <div class="eyebrow">Sample</div>
        <h2 class="h2" style="margin-top:4px">用训练成果出图</h2>
        <div class="divider" style="margin:14px -20px 10px"></div>
        <div class="fields"><FieldRow v-for="f in sampleFields" :key="f.label" :f="f" /></div>
        <div class="foot">
          <button @click="useLatestExport" class="btn btn-soft"><Icon name="download" :size="14" />填入当前运行的最新导出</button>
          <span style="flex:1"></span>
          <button @click="runSample" class="btn btn-lg btn-primary" :disabled="!store.env.backend"><Icon name="image" :size="15" />出图</button>
        </div>
      </section>
      <section class="card card-pad" style="flex:1 1 440px;min-width:0">
        <div class="eyebrow">Export</div>
        <h2 class="h2" style="margin-top:4px">从检查点导出</h2>
        <div class="divider" style="margin:14px -20px 10px"></div>
        <div class="fields"><FieldRow v-for="f in exportFields" :key="f.label" :f="f" /></div>
        <div class="foot">
          <button @click="useLatestCheckpoint" class="btn btn-soft"><Icon name="download" :size="14" />填入当前运行的最新检查点</button>
          <span style="flex:1"></span>
          <button @click="runExport" class="btn btn-lg btn-primary" :disabled="!store.env.backend"><Icon name="box" :size="15" />导出</button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.cols { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start; }
.fields { display: flex; flex-direction: column; gap: 2px; }
.foot { display: flex; align-items: center; gap: 8px; margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--hairline-soft); flex-wrap: wrap; }
</style>
