<script setup>
// 工具页:用训练成果出图(scripts/sample/sample.py)与导出适配器(scripts/export/export.py)。
import { computed, reactive } from 'vue'
import { store, submitJob, toast } from '../store.js'
import { getJson } from '../api.js'
import FieldRow from '../components/FieldRow.vue'

const sample = reactive({
  precision: 'bf16', WEIGHTS: '', TRANSFORMER: '', ADAPTERS: '', PROMPTS: '', NEGATIVE: '',
  H: '1024', W: '1024', STEPS: '50', CFG: '3.0', SEED_BASE: '0', OUT: 'runs/samples', MEMORY_PROFILE: '',
})
const exp = reactive({
  WEIGHTS: '', TRANSFORMER: '', ADAPTER: '', OUT: '', FORMAT: 'comfy', STYLE: 'lora_unet', SAVE_DTYPE: 'bf16', MULTIPLIER: '1.0',
})

const opt = vs => vs.map(v => ({ v, label: v || '默认(常驻)' }))

function mk(model, label, key, type, extra = {}) {
  const v = model[key]
  return {
    label, flag: extra.flag ?? key, hint: extra.hint || '', ph: extra.ph || '', value: v, error: '',
    options: extra.options || [], min: 0, max: 100,
    isPath: type === 'path', isText: type === 'text', isNum: type === 'num', isSelect: type === 'select',
    isArea: type === 'area', isSeg: false, isSlider: false, isSecret: false, segs: [], isOn: false, isOff: false,
    onInput: ev => { model[key] = ev.target.value }, onToggle: () => {},
  }
}

const sampleFields = computed(() => [
  mk(sample, '模型权重', 'WEIGHTS', 'path', { ph: store.form.WEIGHTS || 'ComfyUI/models', hint: '留空 = 训练页的设置' }),
  mk(sample, 'DiT', 'TRANSFORMER', 'path', { ph: store.form.TRANSFORMER || '按变体自动选' }),
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
  mk(exp, '模型权重', 'WEIGHTS', 'path', { ph: store.form.WEIGHTS || 'ComfyUI/models', hint: '留空 = 训练页的设置' }),
  mk(exp, 'DiT', 'TRANSFORMER', 'path', { ph: store.form.TRANSFORMER || '按变体自动选' }),
  mk(exp, '训练状态', 'ADAPTER', 'path', { hint: '检查点里的 trainable.safetensors' }),
  mk(exp, '输出文件', 'OUT', 'path', { ph: 'lora.safetensors' }),
  mk(exp, '格式', 'FORMAT', 'select', { options: opt(['comfy', 'hf', 'lycoris', 'merged', 'diffusers']) }),
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
}

async function useLatestCheckpoint() {
  const r = await latest()
  if (!r?.checkpoints.length) return toast('warn', '还没有检查点 · ' + runDir() + '/checkpoints/')
  exp.ADAPTER = r.checkpoints[0].path + '/trainable.safetensors'
}

const lines = text => text.split('\n').map(s => s.trim()).filter(Boolean)
const weights = w => w || store.form.WEIGHTS || 'ComfyUI/models'
// 留空的模型项沿用训练页(DiT / 变体 / 文本编码器 / VAE 要和训练时一致)
const model = (m, keys) => Object.fromEntries(keys.map(k => [k, m[k] || store.form[k] || '']))

function runSample() {
  if (!lines(sample.PROMPTS).length) return toast('warn', '先写至少一条提示词')
  submitJob('/api/v1/jobs/sample', {
    precision: sample.precision,
    knobs: {
      WEIGHTS: weights(sample.WEIGHTS), VARIANT: store.form.VARIANT || 'base',
      ...model(sample, ['TRANSFORMER', 'TEXT_ENCODER', 'VAE']), ADAPTERS: lines(sample.ADAPTERS), PROMPT: '', PROMPTS: lines(sample.PROMPTS),
      NEGATIVE: sample.NEGATIVE, SIZES: [[sample.H, sample.W]], STEPS: sample.STEPS, CFG: sample.CFG,
      SEED_BASE: sample.SEED_BASE, OUT: sample.OUT, MEMORY_PROFILE: sample.MEMORY_PROFILE,
    },
  }, '出图')
}

function runExport() {
  const knobs = { ...exp, WEIGHTS: weights(exp.WEIGHTS), VARIANT: store.form.VARIANT || 'base', ...model(exp, ['TRANSFORMER']) }
  submitJob('/api/v1/jobs/export', { knobs }, '导出')
}

const card = 'background:var(--surface);border-radius:8px;box-shadow:var(--shadow-card);padding:20px 24px 24px'
const btn = 'height:32px;padding:0 12px;background:var(--surface);border:1px solid var(--hairline);border-radius:6px;font-size:13px;font-weight:500;color:var(--ink);cursor:pointer'
const primary = 'height:36px;padding:0 16px;background:var(--primary);color:var(--on-primary);border:none;border-radius:6px;font-size:14px;font-weight:500;cursor:pointer'
</script>

<template>
  <div style="animation:pageIn .24s cubic-bezier(.2,.8,.2,1) both;max-width:1280px;margin:0 auto">
    <h1 style="margin:0;font-size:20px;line-height:28px;font-weight:600;color:var(--ink)">出图与导出</h1>
    <p style="margin:4px 0 24px;font-size:14px;line-height:20px;color:var(--body)">都作为作业排队,日志在终端;出的图在产物页按输出目录查看。</p>
    <div style="display:flex;flex-wrap:wrap;gap:32px;align-items:flex-start">
      <section :style="card + ';flex:1 1 560px;min-width:0'">
        <div style="font-family:var(--font-mono);font-size:12px;letter-spacing:.5px;color:var(--mute)">SAMPLE</div>
        <h2 style="margin:6px 0 16px;font-size:16px;font-weight:600;color:var(--ink)">用训练成果出图</h2>
        <div style="display:flex;flex-direction:column;gap:16px">
          <FieldRow v-for="f in sampleFields" :key="f.label" :f="f" />
        </div>
        <div style="display:flex;gap:8px;margin-top:20px">
          <button @click="useLatestExport" class="hv-border" :style="btn">用当前运行的最新导出</button>
          <span style="flex:1"></span>
          <button @click="runSample" class="hv-fade" :style="primary">出图</button>
        </div>
      </section>
      <section :style="card + ';flex:1 1 440px;min-width:0'">
        <div style="font-family:var(--font-mono);font-size:12px;letter-spacing:.5px;color:var(--mute)">EXPORT</div>
        <h2 style="margin:6px 0 16px;font-size:16px;font-weight:600;color:var(--ink)">从检查点导出</h2>
        <div style="display:flex;flex-direction:column;gap:16px">
          <FieldRow v-for="f in exportFields" :key="f.label" :f="f" />
        </div>
        <div style="display:flex;gap:8px;margin-top:20px">
          <button @click="useLatestCheckpoint" class="hv-border" :style="btn">用当前运行的最新检查点</button>
          <span style="flex:1"></span>
          <button @click="runExport" class="hv-fade" :style="primary">导出</button>
        </div>
      </section>
    </div>
  </div>
</template>
