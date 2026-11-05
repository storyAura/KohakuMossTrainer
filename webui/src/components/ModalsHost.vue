<script setup>
// 弹窗:停止作业确认、生成的 kogine 配置预览(含校验问题)。
import { store, closeModal, confirmCancel, toast } from '../store.js'

function copyConfig() {
  navigator.clipboard?.writeText(store.configText)
  toast('info', '配置已复制')
}

const overlay = 'position:fixed;inset:0;z-index:100;background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;padding:24px;animation:overlayIn .16s ease both'
const card = 'max-width:100%;background:var(--surface);border-radius:12px;box-shadow:var(--shadow-modal);padding:24px;animation:modalIn .22s cubic-bezier(.2,.8,.2,1) both'
const ghost = 'height:36px;padding:0 14px;background:var(--surface);border:1px solid var(--hairline);border-radius:6px;font-size:14px;font-weight:500;color:var(--ink);cursor:pointer'
</script>

<template>
  <div v-if="store.modal === 'cancel'" :style="overlay">
    <div :style="card + ';width:480px'">
      <h3 style="margin:0;font-size:16px;line-height:24px;font-weight:600;color:var(--ink)">停止当前作业?</h3>
      <p style="margin:8px 0 0;font-size:14px;line-height:20px;color:var(--body)">正在运行的作业会被中断(10 秒后强制结束),排队中的同组作业一起取消。已保存的检查点会保留,可用「从检查点恢复」= latest 接着训练。</p>
      <div style="margin-top:16px;background:var(--surface-2);border-radius:6px;padding:10px 12px;font-family:var(--font-mono);font-size:12px;line-height:20px;color:var(--body)">
        <div v-for="j in store.jobs" :key="j.id">{{ j.id }}  {{ j.kind }}  {{ j.status }}</div>
      </div>
      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:20px">
        <button @click="closeModal" :style="ghost">继续运行</button>
        <button @click="confirmCancel" class="hv-danger"
          style="height:36px;padding:0 14px;background:var(--surface);border:1px solid var(--error);border-radius:6px;font-size:14px;font-weight:500;color:var(--error);cursor:pointer">停止</button>
      </div>
    </div>
  </div>

  <div v-if="store.modal === 'config'" :style="overlay">
    <div :style="card + ';width:760px'">
      <h3 style="margin:0;font-size:16px;line-height:24px;font-weight:600;color:var(--ink)">将要写入的配置</h3>
      <p style="margin:8px 0 0;font-size:14px;line-height:20px;color:var(--body)">提交时写到 <span style="font-family:var(--font-mono)">{{ store.configPath }}</span>,命令行也能直接用:<span style="font-family:var(--font-mono)">kogine run scripts/train/moss.py --config {{ store.configPath }}</span></p>
      <div v-if="store.problems.length" style="margin-top:12px;background:var(--error-soft);border:1px solid var(--error);border-radius:6px;padding:8px 12px">
        <div v-for="(p, i) in store.problems" :key="i" style="font-family:var(--font-mono);font-size:12px;line-height:18px;color:var(--ink)">• {{ p }}</div>
      </div>
      <pre style="margin:16px 0 0;background:var(--terminal-bg);color:#ededed;border-radius:6px;padding:14px 16px;max-height:420px;overflow:auto;font-family:var(--font-mono);font-size:12px;line-height:18px">{{ store.configText }}</pre>
      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:20px">
        <button @click="closeModal" :style="ghost">关闭</button>
        <button @click="copyConfig" class="hv-fade"
          style="height:36px;padding:0 14px;background:var(--primary);color:var(--on-primary);border:none;border-radius:6px;font-size:14px;font-weight:500;cursor:pointer">复制</button>
      </div>
    </div>
  </div>
</template>
