<script setup>
// 作业状态胶囊:运行中蓝色呼吸点,完成绿色,失败红色,取消中琥珀色,其余灰色。
import { computed } from 'vue'

const props = defineProps({ status: { type: String, required: true } })

// [文案, 胶囊样式, 是否呼吸]
const MAP = {
  idle: ['空闲', 'chip-neutral', false],
  queued: ['排队中', 'chip-neutral', true],
  running: ['运行中', 'chip-primary', true],
  cancelling: ['取消中', 'chip-warning', true],
  cancelled: ['已取消', 'chip-neutral', false],
  succeeded: ['已完成', 'chip-success', false],
  failed: ['失败', 'chip-error', false],
}

const m = computed(() => MAP[props.status] || MAP.idle)
</script>

<template>
  <span :class="['chip', m[1]]"><span :class="['dot', { live: m[2] }]"></span>{{ m[0] }}</span>
</template>
