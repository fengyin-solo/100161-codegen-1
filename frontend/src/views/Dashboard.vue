<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常；下方是应急演练台账的待办与评估结论，与演练计划入口同源。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/drill">进入演练台账</RouterLink>
      </div>
    </header>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>
    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>今日新增</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ row.label ?? row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>

    <section class="drill-overview">
      <header class="page-head">
        <div>
          <h3>应急演练评估概览</h3>
          <p class="page-desc">演练状态分待实施、演练中、已评估三段；评估结论取自演练台账同一份数据，在演练计划入口修改后这里同步更新。</p>
        </div>
      </header>
      <div class="stat-row">
        <article v-for="item in drill.counts" :key="item.label" class="stat-card">
          <span class="stat-label">{{ item.label }}</span>
          <strong class="stat-value">{{ item.value }}</strong>
        </article>
      </div>

      <div class="drill-cols">
        <div class="drill-col">
          <h4 class="drill-col-title">待办清单（{{ drill.todo.length }}）</h4>
          <table class="data-table">
            <thead>
              <tr><th>演练编号</th><th>演练科目</th><th>计划日期</th><th>状态</th></tr>
            </thead>
            <tbody>
              <tr v-for="item in drill.todo" :key="String(item.id)">
                <td>{{ item['演练编号'] }}</td>
                <td>{{ item['演练科目'] }}</td>
                <td>{{ item['计划日期'] }}</td>
                <td><span class="status-tag" :class="item.status === '演练中' ? 'status-running' : 'status-todo'">{{ item.status }}</span></td>
              </tr>
              <tr v-if="!drill.todo.length">
                <td colspan="4" class="empty-state">暂无待办演练计划</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="drill-col">
          <h4 class="drill-col-title">评估结论（{{ drill.assessed.length }}）</h4>
          <table class="data-table">
            <thead>
              <tr><th>演练编号</th><th>演练科目</th><th>评估结论</th><th>发现问题</th></tr>
            </thead>
            <tbody>
              <tr v-for="item in drill.assessed" :key="String(item.id)">
                <td>{{ item['演练编号'] }}</td>
                <td>{{ item['演练科目'] }}</td>
                <td><span class="cell-clamp" :title="item['评估结论']">{{ item['评估结论'] || '—' }}</span></td>
                <td>
                  <span v-if="item['发现问题']" class="cell-clamp issue-text" :title="item['发现问题']">{{ item['发现问题'] }}</span>
                  <span v-else>—</span>
                </td>
              </tr>
              <tr v-if="!drill.assessed.length">
                <td colspan="4" class="empty-state">暂无已评估演练</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'

type ModuleRow = { name: string; label?: string; created: number; pending: number; abnormal: number }
type DrillItem = {
  id: number
  status: string
  pending?: boolean
  abnormal?: boolean
  '演练编号': string
  '演练科目': string
  '参演单位'?: string
  '计划日期': string
  '组织人'?: string
  '评估结论': string
  '发现问题': string
}
type DrillSection = {
  module: string
  counts: { label: string; value: number }[]
  todo: DrillItem[]
  assessed: DrillItem[]
}
type Overview = {
  cards: { label: string; value: number }[]
  modules: ModuleRow[]
  drill: DrillSection
}

const emptyDrill: DrillSection = {
  module: 'drill',
  counts: [
    { label: '待实施', value: 0 },
    { label: '演练中', value: 0 },
    { label: '已评估', value: 0 },
  ],
  todo: [],
  assessed: [],
}

const cards = ref<Overview['cards']>([])
const moduleRows = ref<ModuleRow[]>([])
const drill = ref<DrillSection>(emptyDrill)

onMounted(async () => {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
    drill.value = payload.drill ?? emptyDrill
  } catch {
    cards.value = [{ label: '业务模块', value: 0 }, { label: '今日新增', value: 0 }]
    moduleRows.value = []
    drill.value = emptyDrill
  }
})
</script>
