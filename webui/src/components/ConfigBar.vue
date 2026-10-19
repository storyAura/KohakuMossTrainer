<script setup>
// 配置文件栏(仿 kohya_ss 的 Load/Save Config file):路径框 + 已有配置下拉、
// 打开 / 保存(训练机上的文件)、导出 / 导入(浏览器所在电脑上的文件)。
import { ref } from 'vue'
import { store, listConfigs, openConfig, saveConfig, exportConfig, importConfig } from '../store.js'

const picker = ref(null)

function onPick(ev) {
  const file = ev.target.files?.[0]
  if (file) importConfig(file)
  ev.target.value = ''
}

const btn = 'height:34px;padding:0 12px;background:var(--surface);border:1px solid var(--hairline);border-radius:6px;font-size:13px;font-weight:500;color:var(--ink);white-space:nowrap;cursor:pointer'
</script>

<template>
  <section style="background:var(--surface);border-radius:8px;box-shadow:var(--shadow-card);padding:14px 16px;margin-bottom:24px">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <span style="font-family:var(--font-mono);font-size:12px;letter-spacing:.5px;color:var(--mute);margin-right:4px">CONFIG</span>
      <input v-model="store.cfgFile" list="config-files" @focus="listConfigs" @keydown.enter="openConfig"
        :placeholder="(store.caps.config_dir || 'configs/user/webui') + '/<名字>.json'"
        style="flex:1;min-width:260px;height:34px;padding:0 10px;background:var(--surface);border:1px solid var(--hairline);border-radius:6px;font-family:var(--font-mono);font-size:13px;color:var(--ink)" />
      <datalist id="config-files"><option v-for="f in store.cfgFiles" :key="f.path" :value="f.path" /></datalist>
      <button @click="listConfigs" class="hv-border" :style="btn" title="刷新已有配置列表">↻</button>
      <button @click="openConfig" class="hv-border" :style="btn">打开</button>
      <button @click="saveConfig" class="hv-fade"
        style="height:34px;padding:0 14px;background:var(--primary);color:var(--on-primary);border:none;border-radius:6px;font-size:13px;font-weight:500;cursor:pointer">保存</button>
      <span style="width:1px;height:20px;background:var(--hairline);margin:0 4px"></span>
      <button @click="exportConfig" class="hv-border" :style="btn" title="下载到本机">导出</button>
      <button @click="picker.click()" class="hv-border" :style="btn" title="从本机选择 .json">导入</button>
      <input ref="picker" type="file" accept=".json,application/json" @change="onPick" style="display:none" />
    </div>
    <div style="font-size:12px;line-height:16px;color:var(--mute);margin-top:8px">
      打开 / 保存读写训练机上的文件(改个路径再保存 = 另存为;留空保存到 configs/user/webui/&lt;运行名&gt;.json);导出 / 导入是浏览器这台电脑上的文件。开始训练时也会自动保存一份。
    </div>
  </section>
</template>
