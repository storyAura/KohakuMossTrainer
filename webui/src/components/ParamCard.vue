<script setup>
// 一张分组参数卡:头部点击折叠(折叠后仍显示改动数 / 问题数)、字段列表、高级参数二级折叠;
// 数据集卡附带数据集编辑器。
import FieldRow from './FieldRow.vue'
import DatasetFields from './DatasetFields.vue'
import Icon from './Icon.vue'

defineProps({ g: { type: Object, required: true } })
</script>

<template>
  <section :id="'group-' + g.key" class="card group">
    <button class="head" @click="g.toggleCollapse" :aria-expanded="!g.collapsed">
      <div class="head-text">
        <div class="eyebrow">{{ g.eyebrow }}</div>
        <div class="title-line">
          <h2 class="h2">{{ g.title }}</h2>
          <span v-if="g.dirtyCount" class="chip chip-warning">已改 {{ g.dirtyCount }}</span>
          <span v-if="g.errorCount" class="chip chip-error">{{ g.errorCount }} 个问题</span>
        </div>
      </div>
      <span :class="['caret', { shut: g.collapsed }]"><Icon name="chevron" :size="16" /></span>
    </button>
    <div :class="['body-wrap', { shut: g.collapsed }]">
      <div class="body">
        <div class="divider" style="margin:14px -20px 10px"></div>
        <div class="fields">
          <FieldRow v-for="f in g.fields" :key="f.flag" :f="f" />
        </div>

        <DatasetFields v-if="g.custom === 'datasets'" />

        <div v-if="g.advOpen" class="adv">
          <FieldRow v-for="f in g.advFields" :key="f.flag" :f="f" />
        </div>

        <button v-if="g.hasAdv" @click="g.toggleAdv" class="link-btn adv-btn">
          <span :class="['caret-sm', { open: g.advOpen }]"><Icon name="chevron" :size="13" /></span>
          {{ g.advLabel }}
          <span v-if="!g.advOpen && g.advDirty" class="chip chip-warning" style="height:18px;font-size:10px">已改 {{ g.advDirty }}</span>
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.group { padding: 0 22px; scroll-margin-top: 140px; }
.head {
  width: 100%; display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
  padding: 18px 0 0; background: none; border: none; text-align: left; cursor: pointer; color: inherit;
}
.head-text { min-width: 0; }
.title-line { display: flex; align-items: center; gap: 8px; margin-top: 4px; flex-wrap: wrap; }
.caret { color: var(--faint); margin-top: 4px; transition: transform var(--t-base) var(--ease); }
.caret.shut { transform: rotate(-90deg); }
.head:hover .caret { color: var(--ink); }
.body-wrap { display: grid; grid-template-rows: 1fr; transition: grid-template-rows var(--t-sheet) var(--ease); }
.body-wrap.shut { grid-template-rows: 0fr; }
.body { min-height: 0; overflow: hidden; padding-bottom: 18px; }
.body-wrap.shut .body { padding-bottom: 16px; }
.fields { display: flex; flex-direction: column; gap: 2px; }
.adv { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--hairline); display: flex; flex-direction: column; gap: 2px; animation: rowIn var(--t-base) var(--ease) both; }
.adv-btn { margin-top: 12px; color: var(--mute); font-size: 13px; }
.adv-btn:hover { color: var(--primary); text-decoration: none; }
.caret-sm { display: inline-flex; transform: rotate(-90deg); transition: transform var(--t-base) var(--ease); }
.caret-sm.open { transform: none; }
</style>
