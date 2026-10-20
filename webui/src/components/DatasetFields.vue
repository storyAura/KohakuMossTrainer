<script setup>
// 多数据集编辑器(DATASETS 的 path / weight)+ 数据准备按钮
// (scripts/data/ 的检查数据、缓存文字、缓存图片,用同一份 _data.py 配置)。
import { store, addDataset, removeDataset, setDataset, prepareData } from '../store.js'

const inputStyle = 'height:34px;padding:0 10px;background:var(--surface);border:1px solid var(--hairline);border-radius:6px;font-family:var(--font-mono);font-size:13px;color:var(--ink)'
const btn = 'height:32px;padding:0 12px;background:var(--surface);border:1px solid var(--hairline);border-radius:6px;font-size:13px;font-weight:500;color:var(--ink);white-space:nowrap;cursor:pointer'
</script>

<template>
  <div style="display:flex;flex-direction:column;gap:12px;margin-top:16px">
    <div v-for="(d, i) in store.datasets" :key="i"
      style="display:grid;grid-template-columns:minmax(0,1fr) 88px auto;gap:8px;align-items:center;animation:cardIn .2s ease both">
      <input :value="d.path" @input="setDataset(i, 'path', $event.target.value)" placeholder="数据集的完整路径,如 /root/data/my_set(或 jsonl / parquet 文件)" :style="inputStyle + ';width:100%'" />
      <input :value="d.weight" @input="setDataset(i, 'weight', $event.target.value)" title="weight:多个数据集时的抽样权重" :style="inputStyle + ';width:88px;text-align:right'" />
      <button @click="removeDataset(i)" :disabled="store.datasets.length <= 1" class="hv-line"
        style="height:34px;padding:0 10px;background:transparent;border:1px solid var(--hairline);border-radius:6px;font-size:12px;color:var(--body);cursor:pointer">移除</button>
    </div>
    <button @click="addDataset" class="hv-line"
      style="height:32px;padding:0 12px;align-self:flex-start;background:transparent;border:1px dashed var(--hairline);border-radius:6px;font-size:13px;font-weight:500;color:var(--body);cursor:pointer">+ 添加数据集</button>

    <div style="margin-top:8px;padding-top:16px;border-top:1px solid var(--hairline);display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <button @click="prepareData(['inspect'])" class="hv-border" :style="btn">检查数据</button>
      <button @click="prepareData(['text'])" class="hv-border" :style="btn">缓存文字描述</button>
      <button @click="prepareData(['latents'])" class="hv-border" :style="btn">缓存图片</button>
      <span style="flex:1"></span>
      <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--body);cursor:pointer">
        <input type="checkbox" :checked="store.prepare" @change="store.prepare = $event.target.checked" style="accent-color:var(--ink)" />
        训练前自动准备数据
      </label>
    </div>
    <div style="font-size:12px;line-height:16px;color:var(--mute)">每份数据做一次即可;缓存只补缺的条目,重复运行很快。</div>
  </div>
</template>
