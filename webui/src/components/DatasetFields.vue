<script setup>
// 多数据集编辑器(DATASETS 的 path / weight)+ 数据准备按钮
// (scripts/data/ 的检查数据、缓存文字、缓存图片,用同一份 _data.py 配置)。
import { store, addDataset, removeDataset, setDataset, prepareData } from '../store.js'
import Icon from './Icon.vue'
</script>

<template>
  <div class="datasets">
    <div class="ds-head">
      <span class="eyebrow">数据集路径</span>
      <span class="eyebrow" style="width:80px;text-align:right">抽样权重</span>
      <span style="width:32px"></span>
    </div>
    <div v-for="(d, i) in store.datasets" :key="i" class="ds-row">
      <input :value="d.path" @input="setDataset(i, 'path', $event.target.value)" spellcheck="false"
        placeholder="数据集目录(或 jsonl / parquet 文件)" class="input mono" />
      <input :value="d.weight" @input="setDataset(i, 'weight', $event.target.value)" inputmode="decimal"
        class="input mono" style="width:80px;text-align:right" />
      <button @click="removeDataset(i)" :disabled="store.datasets.length <= 1" class="btn btn-ghost btn-icon"
        :data-tip="store.datasets.length <= 1 ? '至少保留一个' : '移除这个数据集'">
        <Icon name="trash" :size="15" />
      </button>
    </div>
    <button @click="addDataset" class="btn add"><Icon name="plus" :size="14" />添加数据集</button>

    <div class="prep">
      <div class="prep-btns">
        <button @click="prepareData(['inspect'])" class="btn btn-soft" :disabled="!store.env.backend">检查数据</button>
        <button @click="prepareData(['text'])" class="btn" :disabled="!store.env.backend">缓存文字描述</button>
        <button @click="prepareData(['latents'])" class="btn" :disabled="!store.env.backend">缓存图片</button>
      </div>
      <label class="check">
        <input type="checkbox" :checked="store.prepare" @change="store.prepare = $event.target.checked" />
        训练前自动准备数据
      </label>
    </div>
  </div>
</template>

<style scoped>
.datasets { display: flex; flex-direction: column; gap: 8px; margin-top: 14px; padding: 14px; background: var(--surface-3); border: 1px solid var(--hairline-soft); border-radius: var(--r-md); }
.ds-head { display: flex; gap: 8px; }
.ds-head > :first-child { flex: 1; }
.ds-row { display: flex; gap: 8px; align-items: center; animation: rowIn var(--t-base) var(--ease) both; }
.add { align-self: flex-start; border-style: dashed; box-shadow: none; background: transparent; }
.prep { margin-top: 6px; padding-top: 12px; border-top: 1px solid var(--hairline); display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
.prep-btns { display: flex; gap: 6px; flex-wrap: wrap; }
</style>
