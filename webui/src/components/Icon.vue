<script setup>
// 线性图标(Lucide 风格,24 网格、描边 currentColor),内联 SVG,不依赖外部字体。
import { computed } from 'vue'

const props = defineProps({ name: { type: String, required: true }, size: { type: Number, default: 16 } })

const P = d => `<path d="${d}"/>`
const ICONS = {
  train: ['M21 4h-7', 'M10 4H3', 'M21 12h-9', 'M8 12H3', 'M21 20h-5', 'M12 20H3', 'M14 2v4', 'M8 10v4', 'M16 18v4'].map(P).join(''),
  image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/>' + P('m21 15-3.09-3.09a2 2 0 0 0-2.82 0L6 21'),
  queue: ['M3 6h.01', 'M3 12h.01', 'M3 18h.01', 'M8 6h13', 'M8 12h13', 'M8 18h13'].map(P).join(''),
  folder: P('M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z'),
  box: ['M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z', 'm3.3 7 8.7 5 8.7-5', 'M12 22V12'].map(P).join(''),
  bookmark: P('m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z'),
  cpu: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/>' +
    ['M15 2v2', 'M15 20v2', 'M2 15h2', 'M2 9h2', 'M20 15h2', 'M20 9h2', 'M9 2v2', 'M9 20v2'].map(P).join(''),
  sun: '<circle cx="12" cy="12" r="4"/>' +
    ['M12 2v2', 'M12 20v2', 'm4.93 4.93 1.41 1.41', 'm17.66 17.66 1.41 1.41', 'M2 12h2', 'M20 12h2', 'm6.34 17.66-1.41 1.41', 'm19.07 4.93-1.41 1.41'].map(P).join(''),
  moon: P('M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z'),
  monitor: '<rect x="2" y="3" width="20" height="14" rx="2"/>' + P('M8 21h8') + P('M12 17v4'),
  play: P('M6 3 20 12 6 21Z'),
  stop: '<rect x="6" y="6" width="12" height="12" rx="1.5"/>',
  copy: '<rect x="8" y="8" width="14" height="14" rx="2"/>' + P('M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2'),
  reset: P('M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8') + P('M3 3v5h5'),
  refresh: ['M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8', 'M21 3v5h-5', 'M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16', 'M8 16H3v5'].map(P).join(''),
  chevron: P('m6 9 6 6 6-6'),
  pin: P('M12 17v5') + P('M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z'),
  x: P('M18 6 6 18') + P('m6 6 12 12'),
  check: P('M20 6 9 17l-5-5'),
  info: '<circle cx="12" cy="12" r="10"/>' + P('M12 16v-4') + P('M12 8h.01'),
  checkCircle: '<circle cx="12" cy="12" r="10"/>' + P('m9 12 2 2 4-4'),
  alert: P('m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3') + P('M12 9v4') + P('M12 17h.01'),
  file: P('M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z') + P('M14 2v6h6') + P('m10 13-2 2 2 2') + P('m14 17 2-2-2-2'),
  download: P('M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4') + P('m7 10 5 5 5-5') + P('M12 15V3'),
  plus: P('M5 12h14') + P('M12 5v14'),
  trash: P('M3 6h18') + P('M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6') + P('M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2'),
  expand: ['M8 3H5a2 2 0 0 0-2 2v3', 'M21 8V5a2 2 0 0 0-2-2h-3', 'M3 16v3a2 2 0 0 0 2 2h3', 'M16 21h3a2 2 0 0 0 2-2v-3'].map(P).join(''),
  arrowDown: P('M12 5v14') + P('m19 12-7 7-7-7'),
  activity: P('M22 12h-4l-3 9L9 3l-3 9H2'),
  columns: '<rect x="3" y="3" width="18" height="18" rx="2"/>' + P('M12 3v18'),
  rows: '<rect x="3" y="3" width="18" height="18" rx="2"/>' + P('M3 12h18'),
  layers: P('m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z') + P('m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65') + P('m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65'),
  zap: P('M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z'),
}

const html = computed(() => ICONS[props.name] || '')
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="flex-shrink:0;display:block" v-html="html"></svg>
</template>
