<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常。</p>
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
          <td>{{ row.label || row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>
    <section class="overview-section">
      <div class="section-head">
        <h3>应急演练评估结论</h3>
        <RouterLink class="section-link" to="/drill">进入演练计划入口</RouterLink>
      </div>
      <table class="data-table">
        <thead>
          <tr><th>演练科目</th><th>参演单位</th><th>计划日期</th><th>组织人</th><th>评估结论</th><th>发现问题</th></tr>
        </thead>
        <tbody>
          <tr v-for="item in drillEvaluations" :key="String(item.id)">
            <td>{{ item['演练科目'] }}</td>
            <td>{{ item['参演单位'] }}</td>
            <td>{{ item['计划日期'] }}</td>
            <td>{{ item['组织人'] }}</td>
            <td>{{ item['评估结论'] }}</td>
            <td>{{ item['发现问题'] || '—' }}</td>
          </tr>
          <tr v-if="!drillEvaluations.length">
            <td colspan="6" class="empty-state">暂无已评估的应急演练记录</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'

type ModuleRow = { name: string; label?: string; created: number; pending: number; abnormal: number }
type DrillEvaluation = {
  id: number
  演练科目: string
  参演单位: string
  计划日期: string
  组织人: string
  评估结论: string
  发现问题: string
}

type Overview = {
  cards: { label: string; value: number }[]
  modules: ModuleRow[]
  drill_evaluations?: DrillEvaluation[]
}

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>([])
const drillEvaluations = ref<DrillEvaluation[]>([])

onMounted(async () => {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
    drillEvaluations.value = payload.drill_evaluations ?? []
  } catch {
    cards.value = [{"label": "业务模块", "value": 0}, {"label": "今日新增", "value": 0}]
    moduleRows.value = [{"name": "航班计划", "created": 0, "pending": 0, "abnormal": 0}, {"name": "机位资源", "created": 0, "pending": 0, "abnormal": 0}, {"name": "机坪巡查", "created": 0, "pending": 0, "abnormal": 0}, {"name": "廊桥对接", "created": 0, "pending": 0, "abnormal": 0}, {"name": "除冰作业", "created": 0, "pending": 0, "abnormal": 0}, {"name": "航油加注", "created": 0, "pending": 0, "abnormal": 0}, {"name": "行李装卸", "created": 0, "pending": 0, "abnormal": 0}, {"name": "货邮装载", "created": 0, "pending": 0, "abnormal": 0}, {"name": "航空配餐", "created": 0, "pending": 0, "abnormal": 0}, {"name": "摆渡接送", "created": 0, "pending": 0, "abnormal": 0}, {"name": "航空器牵引", "created": 0, "pending": 0, "abnormal": 0}, {"name": "载重平衡", "created": 0, "pending": 0, "abnormal": 0}, {"name": "通行证件", "created": 0, "pending": 0, "abnormal": 0}, {"name": "保障车辆", "created": 0, "pending": 0, "abnormal": 0}, {"name": "安全监察", "created": 0, "pending": 0, "abnormal": 0}, {"name": "保障协议", "created": 0, "pending": 0, "abnormal": 0}, {"name": "保障结算", "created": 0, "pending": 0, "abnormal": 0}, {"name": "资质培训", "created": 0, "pending": 0, "abnormal": 0}]
  }
})
</script>
