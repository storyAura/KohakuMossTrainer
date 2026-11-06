// 指标曲线的纯函数:数字显示、EMA 平滑、跟随最新时的横轴范围。

export function fmtMetric(v) {
  if (v === null || v === undefined || !Number.isFinite(v)) return '-'
  const a = Math.abs(v)
  if (a === 0) return '0'
  if (a >= 1000) return v.toFixed(0)
  if (a >= 1) return v.toFixed(3)
  if (a >= 0.01) return v.toFixed(4)
  return v.toExponential(2)
}

// 和 TensorBoard 一样的指数平滑;weight 是 0~99 的滑杆值
export function ema(values, weight) {
  const w = Math.min(0.99, Math.max(0, weight / 100))
  let last = null
  return values.map(v => {
    if (!Number.isFinite(v)) return v
    last = last === null ? v : last * w + v * (1 - w)
    return last
  })
}

// 最近 percent% 步数的横轴范围;percent >= 100 或没数据时为整段
export function recentWindow(data, percent) {
  if (!data.length) return null
  const first = data[0][0], last = data[data.length - 1][0]
  const span = Math.max(1, last - first)
  return { start: percent >= 100 ? first : Math.max(first, last - span * percent / 100), end: last }
}
