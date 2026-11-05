<script setup>
// 作业队列:后端 /api/v1/jobs 的全部作业(串行执行,同一时间只跑一个);进行中的可停止。
import { onMounted, onUnmounted } from 'vue'
import { store, loadQueue, cancelJob } from '../store.js'
import StatusBadge from '../components/StatusBadge.vue'

let timer = null
onMounted(() => { loadQueue(); timer = setInterval(loadQueue, 3000) })
onUnmounted(() => clearInterval(timer))

const progress = j => j.progress.total ? j.progress.step + '/' + j.progress.total : '—'
const live = j => ['queued', 'running', 'cancelling'].includes(j.status)
const cols = 'display:grid;grid-template-columns:110px 1fr 110px 110px 70px 80px 64px;gap:12px;padding:0 16px;align-items:center'
const head = 'font-family:var(--font-mono);font-size:12px;letter-spacing:.5px;color:var(--mute)'
const cell = 'font-family:var(--font-mono);font-size:13px;color:var(--body);font-variant-numeric:tabular-nums'
</script>

<template>
  <div style="animation:pageIn .24s cubic-bezier(.2,.8,.2,1) both;max-width:1280px;margin:0 auto">
    <h1 style="margin:0;font-size:20px;line-height:28px;font-weight:600;color:var(--ink)">作业队列</h1>
    <p style="margin:4px 0 24px;font-size:14px;line-height:20px;color:var(--body)">同一时间只跑一个作业(一张卡);同组作业中某步失败,后面的会自动取消。后端重启后列表清空。</p>
    <section style="background:var(--surface);border-radius:8px;box-shadow:var(--shadow-card);overflow-x:auto">
      <div :style="cols + ';height:36px;background:var(--surface-2);border-bottom:1px solid var(--hairline)'">
        <span :style="head">JOB_ID</span><span :style="head">KIND</span><span :style="head">STATUS</span>
        <span :style="head + ';text-align:right'">PROGRESS</span><span :style="head + ';text-align:right'">START</span>
        <span :style="head + ';text-align:right'">TIME</span><span></span>
      </div>
      <div v-if="!store.queue.length" style="height:96px;display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:12px;color:var(--mute)">还没有作业</div>
      <div v-for="j in store.queue" :key="j.job_id" class="hv-row" :title="j.config"
        :style="cols + ';min-height:44px;border-bottom:1px solid var(--hairline)'">
        <span style="font-family:var(--font-mono);font-size:13px;color:var(--ink)">{{ j.job_id }}</span>
        <div style="min-width:0">
          <div style="font-family:var(--font-mono);font-size:13px;color:var(--ink)">{{ j.kind }}</div>
          <div style="font-size:12px;line-height:16px;color:var(--mute);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ j.note }}</div>
        </div>
        <div><StatusBadge :status="j.status" /></div>
        <span :style="cell + ';text-align:right'">{{ progress(j) }}</span>
        <span :style="cell + ';text-align:right'">{{ j.started }}</span>
        <span :style="cell + ';text-align:right'">{{ j.duration }}</span>
        <button v-if="live(j)" @click="cancelJob(j.job_id)" class="hv-line"
          style="height:28px;background:transparent;border:1px solid var(--hairline);border-radius:6px;font-size:12px;color:var(--body);cursor:pointer">停止</button>
        <span v-else-if="j.exit_code" :style="cell + ';color:var(--error)'">exit {{ j.exit_code }}</span>
        <span v-else></span>
      </div>
    </section>
  </div>
</template>
