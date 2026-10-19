<script setup>
// 一个指标的曲线(ECharts):滚轮缩放、拖拽平移;loss 类可叠一条 EMA 平滑线(原始线淡显)。
// 同 group 的图缩放、悬停联动。window 为 null 时保留用户自己缩放的范围。
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { DataZoomComponent, GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { store } from '../store.js'
import { ema, fmtMetric } from '../metrics.js'

echarts.use([LineChart, DataZoomComponent, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  name: { type: String, required: true },
  data: { type: Array, required: true }, // [[step, value], ...]
  smooth: { type: Number, default: 0 }, // 0~99
  smoothable: { type: Boolean, default: false },
  window: { type: Object, default: null }, // { start, end } 步数范围;null = 用户自己缩放
  group: { type: String, default: 'metrics' },
})
const emit = defineEmits(['zoomed'])

const el = ref(null)
let chart = null
let resize = null
let zoomSet = false

const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim()

function render() {
  if (!chart) return
  const accent = css('--accent'), axis = css('--mute'), grid = css('--hairline')
  const line = (data, width, opacity, z) => ({
    type: 'line', data, showSymbol: false, sampling: 'lttb', z,
    lineStyle: { color: accent, width, opacity }, itemStyle: { color: accent, opacity },
  })
  const smoothOn = props.smoothable && props.smooth > 0
  const series = [line(props.data, 1.2, smoothOn ? 0.28 : 1, 1)]
  if (smoothOn) {
    const s = ema(props.data.map(p => p[1]), props.smooth)
    series.push(line(props.data.map((p, i) => [p[0], s[i]]), 2.2, 1, 3))
  }
  const option = {
    animation: false,
    grid: { left: 56, right: 16, top: 12, bottom: 24 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: css('--surface'),
      borderColor: grid,
      textStyle: { color: css('--ink'), fontSize: 12, fontFamily: 'JetBrains Mono, monospace' },
      formatter: ps => {
        if (!ps?.length) return ''
        const rows = ps.map(p => (ps.length > 1 ? (p.seriesIndex ? 'smooth ' : 'raw ') : '') + fmtMetric(p.value[1]))
        return 'step ' + ps[0].value[0] + '<br>' + rows.join('<br>')
      },
    },
    xAxis: {
      type: 'value', min: 'dataMin', max: 'dataMax',
      axisLine: { lineStyle: { color: axis, opacity: 0.4 } }, axisTick: { show: false },
      axisLabel: { color: axis, fontSize: 10 }, splitLine: { lineStyle: { color: grid } },
    },
    yAxis: {
      type: 'value', scale: true, axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: axis, fontSize: 10, formatter: fmtMetric }, splitLine: { lineStyle: { color: grid } },
    },
    series,
  }
  // 跟随范围(或第一次画)时才重设缩放;用户缩放过就保持不动
  const setZoom = props.window || !zoomSet
  if (setZoom) {
    option.dataZoom = [{
      type: 'inside', xAxisIndex: 0, filterMode: 'none',
      zoomOnMouseWheel: true, moveOnMouseMove: true, moveOnMouseWheel: false,
      ...(props.window ? { startValue: props.window.start, endValue: props.window.end } : {}),
    }]
    zoomSet = true
  }
  chart.setOption(option, { replaceMerge: setZoom ? ['series', 'dataZoom'] : ['series'] })
}

onMounted(() => {
  chart = echarts.init(el.value, null, { renderer: 'canvas' })
  chart.group = props.group
  echarts.connect(props.group)
  chart.on('dataZoom', () => emit('zoomed'))
  resize = new ResizeObserver(() => chart?.resize())
  resize.observe(el.value)
  render()
})

onBeforeUnmount(() => {
  resize?.disconnect()
  chart?.dispose()
  chart = null
})

watch(() => [props.data, props.smooth, props.window, store.theme], render)
</script>

<template>
  <div ref="el" style="width:100%;height:220px"></div>
</template>
