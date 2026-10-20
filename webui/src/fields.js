// 训练表单字段表:key 是 scripts/train/moss.py 的旋钮名(KNOB 或 KNOB.字段),
// type 决定控件与提交格式:lines=每行一项的列表,list=逗号分隔,json=JSON 文本,
// layer:<组>=预设层选择(configs/moss/<组>/),其余与 FieldRow 控件同名。

const opt = (...vs) => vs.map(v => ({ v }))

export const GROUPS = [
  {
    key: 'basic', eyebrow: 'BASIC', title: '基础',
    desc: '算法、显存档位、精度选的是 configs/moss/ 下的预设层;切换后下方参数会按该组合刷新(手动改过的不动)。',
    fields: [
      { label: '训练算法', key: 'algo', type: 'layer:algo', hint: 'full = 全量微调' },
      { label: '显存档位', key: 'vram', type: 'layer:vram', hint: '按显卡显存选;auto 由内存规划器挑' },
      { label: '计算精度', key: 'precision', type: 'layer:precision', hint: '20 系及更老的卡用 fp16' },
      { label: '运行名', key: 'RUN_NAME', type: 'text', hint: '输出子目录与配置文件名' },
      { label: '输出目录', key: 'OUTPUT_DIR', type: 'path' },
      { label: '总步数', key: 'STEPS', type: 'num' },
      { label: '省内存模式', key: 'lowRam', type: 'toggle', special: true, hint: '内存 < 32 GB 建议:底模 int8、关闭训练中采样' },
    ],
    adv: [],
  },
  {
    key: 'model', eyebrow: 'MODEL', title: '模型',
    desc: '权重格式:comfy = ComfyUI models 文件夹(int8 单文件,默认),hf = 官方 HF 文件夹。模型页可一键下载。',
    fields: [
      { label: '权重格式', key: 'weights', type: 'layer:weights' },
      { label: '模型权重', key: 'WEIGHTS', type: 'path', hint: 'ComfyUI models 文件夹或 HF 模型目录' },
      { label: '变体', key: 'VARIANT', type: 'seg', options: opt('base', 'sft') },
      { label: 'DiT', key: 'TRANSFORMER', type: 'path', ph: '留空 = 按变体自动选', hint: 'diffusion_models/ 下的文件名或路径' },
      { label: '文本编码器', key: 'TEXT_ENCODER', type: 'path', ph: '留空 = 自动选' },
      { label: 'VAE', key: 'VAE', type: 'path', ph: '留空 = 自动选' },
    ],
    adv: [
      { label: '文本编码器放置', key: 'TEXT_ENCODE.memory', type: 'select', options: opt('auto', 'resident', 'offload', 'ring') },
      { label: '训练 text refiner', key: 'TRAIN_TEXT_REFINER', type: 'toggle' },
    ],
  },
  {
    key: 'dataset', eyebrow: 'DATASET', title: '数据集', custom: 'datasets',
    desc: '可添加多个数据集;数据格式决定目录怎么读(kohya = <重复次数>_<名字>/ 子目录 + .txt 标签)。',
    fields: [
      { label: '数据格式', key: 'data', type: 'layer:data' },
      { label: '分辨率模式', key: 'RESOLUTION_MODE', type: 'select', options: opt('resize', 'bucket', 'shifted_square', 'square_crop') },
      { label: '目标面积', key: 'TARGET_AREA', type: 'pixels', hint: '宽,高 如 1024,1024 / 1536,1536;也可直接写像素数' },
      { label: '每批 token 上限', key: 'MAX_TOKENS', type: 'num' },
      { label: '打乱标签', key: 'CAPTION.shuffle', type: 'toggle' },
      { label: '标签丢弃率', key: 'CAPTION.tag_dropout', type: 'num' },
      { label: '空提示概率', key: 'TEXT_DROP', type: 'num' },
    ],
    adv: [
      { label: '缓存目录', key: 'CACHE_DIR', type: 'path', ph: '留空 = <数据集>/cache' },
      { label: '缓存精度', key: 'CACHE_DTYPE', type: 'select', options: opt('bf16', 'fp16', 'fp32', 'fp8') },
      { label: '水平翻转', key: 'FLIP', type: 'toggle' },
      { label: '超长样本', key: 'OVERLONG', type: 'select', options: opt('drop', 'truncate_text', 'drop_tokens') },
      { label: '加载进程数', key: 'NUM_WORKERS', type: 'num' },
    ],
  },
  {
    key: 'adapter', eyebrow: 'ADAPTER', title: '网络', hideFor: 'full',
    desc: 'LyCORIS 适配器;全量微调时不显示。',
    fields: [
      { label: '注入位置', key: 'PRESET', type: 'select', options: opt('attn', 'attn-mlp', 'full-block', 'all') },
      { label: '维度', key: 'DIM', type: 'num' },
      { label: 'Alpha', key: 'ALPHA', type: 'num' },
      { label: 'DoRA', key: 'DORA', type: 'toggle' },
      { label: 'LoRA+ 比例', key: 'LORAPLUS_RATIO', type: 'num', hint: '1.0 = 关闭' },
    ],
    adv: [
      { label: '算法参数', key: 'ALGO_KWARGS', type: 'json', hint: '如 {"factor": 8}' },
      { label: 'Dropout', key: 'DROPOUT', type: 'json' },
      { label: '适配器模式', key: 'ADAPTER_MODE', type: 'select', options: opt('bypass', 'merge') },
      { label: '训练 norm', key: 'TRAIN_NORMS', type: 'toggle' },
    ],
  },
  {
    key: 'optim', eyebrow: 'OPTIMIZER', title: '优化器与学习率',
    desc: '学习率调度由 AnySchedule 处理,warmup 单位是步。',
    fields: [
      { label: '优化器', key: 'OPTIMIZER', type: 'select', options: opt('adamw', 'adamw16', 'adamw8bit', 'adamw8bit_kernel', 'muon', 'prodigy', 'schedule_free') },
      { label: '学习率', key: 'LR', type: 'num' },
      { label: '权重衰减', key: 'WEIGHT_DECAY', type: 'num' },
      { label: '调度器', key: 'SCHEDULE.mode', type: 'select', options: opt('cosine', 'constant', 'polynomial', 'power', 'step') },
      { label: '预热步数', key: 'SCHEDULE.warmup', type: 'num' },
      { label: '梯度裁剪', key: 'GRAD_CLIP', type: 'num' },
      { label: '梯度累积', key: 'GRAD_ACC', type: 'num' },
    ],
    adv: [
      { label: '优化器参数', key: 'OPTIMIZER_KWARGS', type: 'json' },
      { label: 'EMA', key: 'EMA', type: 'num', hint: '0 = 关闭' },
      { label: '随机种子', key: 'SEED', type: 'num' },
      { label: '衰减规则', key: 'WD_RULES', type: 'select', options: opt('moss', 'none', 'all') },
    ],
  },
  {
    key: 'objective', eyebrow: 'OBJECTIVE', title: '训练目标',
    desc: '时间步采样与损失函数。',
    fields: [
      { label: '时间步采样', key: 'TIMESTEP', type: 'select', options: opt('moss', 'uniform', 'logit_normal') },
      { label: '损失函数', key: 'LOSS', type: 'select', options: opt('mse', 'huber', 'l1') },
      { label: '损失加权', key: 'WEIGHTING', type: 'select', options: opt('none', 'x0', 'eps') },
    ],
    adv: [{ label: '时间步参数', key: 'TIMESTEP_KWARGS', type: 'json' }],
  },
  {
    key: 'memory', eyebrow: 'MEMORY', title: '显存与速度',
    desc: '显存档位已选好内存方案,这里可以单独覆盖。',
    fields: [
      { label: '内存方案', key: 'MEMORY_PROFILE', type: 'select', options: 'profiles' },
      { label: '底模精度', key: 'BASE_PRECISION', type: 'select', options: [{ v: '', label: '默认' }, ...opt('auto', 'compute', 'int8', 'fp8', 'fp8_compute', 'mxfp8', 'quant')] },
      { label: '编译', key: 'COMPILE', type: 'select', options: opt('off', 'block', 'model') },
    ],
    adv: [
      { label: '检查点', key: 'CHECKPOINT', type: 'text', ph: '默认', hint: '内存方案选 manual 时生效,如 partial:0.2、block、none' },
      { label: 'token 预算', key: 'TOKEN_BUDGET', type: 'select', options: opt('estimate', 'render', 'exact') },
      { label: '内核调优', key: 'TUNE', type: 'select', options: opt('table', 'off') },
      { label: '内核选择', key: 'KERNELS', type: 'json', hint: '如 {"attention_varlen": "triton"}' },
    ],
  },
  {
    key: 'sampling', eyebrow: 'SAMPLING', title: '训练中采样',
    desc: '每 N 步用下面的提示词出图,图片在产物页与右侧预览。',
    fields: [
      { label: '每 N 步采样', key: 'SAMPLE_EVERY', type: 'num', hint: '0 = 关闭' },
      { label: '提示词', key: 'SAMPLE_PROMPTS', type: 'lines', hint: '每行一条' },
      { label: '负面提示词', key: 'SAMPLE_NEGATIVE', type: 'area' },
      { label: '尺寸 (高, 宽)', key: 'SAMPLE_SIZE', type: 'list' },
      { label: '采样步数', key: 'SAMPLE_STEPS', type: 'num' },
      { label: 'CFG', key: 'SAMPLE_CFG', type: 'num' },
    ],
    adv: [
      { label: '种子', key: 'SAMPLE_SEEDS', type: 'list' },
      { label: 'Shift', key: 'SAMPLE_SHIFT', type: 'num' },
    ],
  },
  {
    key: 'save', eyebrow: 'SAVE', title: '保存与导出',
    desc: '训练结束自动导出到 <输出目录>/<运行名>/export/。',
    fields: [
      { label: '每 N 步保存', key: 'SAVE_EVERY', type: 'num' },
      { label: '保留最近 N 个', key: 'KEEP_LAST', type: 'num' },
      { label: '导出格式', key: 'SAVE_FORMAT', type: 'select', options: opt('comfy', 'hf', 'both', 'none'), hint: 'comfy = ComfyUI 文件,hf = diffusers 键名' },
      { label: '同时导出合并模型', key: 'SAVE_MERGED', type: 'toggle' },
      { label: '从检查点恢复', key: 'RESUME', type: 'text', ph: 'latest 或检查点目录' },
    ],
    adv: [
      { label: '检查点内也导出', key: 'CHECKPOINT_EXPORT', type: 'toggle' },
      { label: '每 N 分钟保存', key: 'SAVE_MINUTES', type: 'num' },
    ],
  },
  {
    key: 'logging', eyebrow: 'LOGGING', title: '日志',
    desc: 'wandb 需要先登录。',
    fields: [
      { label: '记录器', key: 'LOGGER', type: 'select', options: opt('console', 'wandb') },
      { label: '项目名', key: 'PROJECT', type: 'text' },
      { label: '每 N 步打印', key: 'LOG_EVERY', type: 'num' },
    ],
    adv: [],
  },
]

export const KNOB_FIELDS = GROUPS.flatMap(g => [...g.fields, ...g.adv])
  .filter(f => !f.special && !f.type.startsWith('layer:'))
export const LAYER_KEYS = GROUPS.flatMap(g => g.fields)
  .filter(f => f.type.startsWith('layer:')).map(f => f.key)

// 数字显示:很小或很大的数用科学记数法(0.0001 -> 1e-4),其余原样
function number(v) {
  const a = Math.abs(v)
  return a && (a < 1e-3 || a >= 1e7) ? v.toExponential().replace('e+', 'e') : String(v)
}

// 像素面积显示:正方形写成 "边,边",否则原数
function pixels(v) {
  const side = Math.sqrt(v)
  return Number.isInteger(side) ? side + ',' + side : String(v)
}

// 像素面积输入:"宽,高" / "宽x高" / "宽*高" 相乘;单个数(含 1e6)原样交给后端
export function parsePixels(text) {
  const parts = String(text).trim().split(/\s*[,x×*]\s*/i)
  if (parts.length !== 2) return String(text).trim()
  const [w, h] = parts.map(Number)
  return Number.isFinite(w) && Number.isFinite(h) ? String(w * h) : String(text).trim()
}

// 后端旋钮值 -> 控件显示值
export function display(type, v) {
  if (type === 'toggle') return !!v
  if (v === null || v === undefined) return ''
  if (type === 'lines') return (v || []).join('\n')
  if (type === 'list') return (v || []).join(', ')
  if (type === 'json') return JSON.stringify(v)
  if (type === 'pixels' && typeof v === 'number') return pixels(v)
  if (typeof v === 'number') return number(v)
  return String(v)
}

// 控件显示值 -> 提交给后端的值(后端按旋钮原类型转换,整数也接受 1e4)
export function submitted(type, v) {
  if (type === 'lines') return String(v).split('\n').map(s => s.trim()).filter(Boolean)
  if (type === 'pixels') return parsePixels(v)
  return v
}

// ---- 配置文件(kohya_ss 式:扁平 JSON,每个表单项一个键) ----

const NUMERIC = /^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i

// 表单显示值 -> 文件值:列表存数组、JSON 存对象、纯数字存数字,其余存原文
export function toFile(type, v) {
  if (type === 'toggle') return !!v
  if (type === 'lines') return submitted(type, v)
  if (type === 'json') {
    try { return JSON.parse(v) } catch { return v }
  }
  if (type === 'num' && NUMERIC.test(String(v).trim())) return Number(v)
  return v
}

// 文件值 -> 表单显示值(手写的文件也认:数字、数组、对象、"true")
export function fromFile(type, v) {
  if (type === 'toggle') return v === true || v === 'true'
  if (v === null || v === undefined) return ''
  if (type === 'lines') return Array.isArray(v) ? v.join('\n') : String(v)
  if (type === 'json') return typeof v === 'object' ? JSON.stringify(v) : String(v)
  if (type === 'list' && Array.isArray(v)) return v.join(', ')
  if (typeof v === 'number') return display(type, v)
  return String(v)
}
