<template>
  <section class="page" data-module="drill">
    <header class="page-head">
      <div>
        <h2>应急演练台账</h2>
        <p class="page-desc">登记演练计划（科目、参演单位、计划日期、组织人），按待实施、演练中、已评估三段流转，演练结束后补录评估结论与发现问题。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记演练计划</button>
        <button class="btn" type="button" @click="exportRows">导出演练台账</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>关键字</span>
        <input v-model="filters.keyword" placeholder="按演练科目、参演单位或编号检索" />
      </label>
      <label class="filter-item">
        <span>计划状态</span>
        <select v-model="filters.status">
          <option value="">全部</option>
          <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <label class="filter-check">
        <input v-model="todoOnly" type="checkbox" />
        <span>只看待办清单</span>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <form v-if="creating" class="inline-form" @submit.prevent="submitCreate">
      <h3>登记演练计划</h3>
      <div class="form-grid">
        <label class="filter-item">
          <span>演练科目 *</span>
          <input v-model="createForm['演练科目']" placeholder="如：航空器偏出跑道应急救援演练" />
        </label>
        <label class="filter-item">
          <span>参演单位 *</span>
          <input v-model="createForm['参演单位']" placeholder="多个单位用顿号分隔" />
        </label>
        <label class="filter-item">
          <span>计划日期 *</span>
          <input v-model="createForm['计划日期']" type="date" />
        </label>
        <label class="filter-item">
          <span>组织人 *</span>
          <input v-model="createForm['组织人']" placeholder="本次演练的组织人" />
        </label>
      </div>
      <div class="form-actions">
        <button class="btn primary" type="submit">提交登记</button>
        <button class="btn ghost" type="button" @click="creating = false">取消</button>
      </div>
    </form>

    <div v-if="evaluating" class="modal-mask" @click.self="closeEvaluate">
      <form class="modal-card" @submit.prevent="submitEvaluate">
        <h3>补录演练评估</h3>
        <p class="modal-tip">
          {{ evaluating['演练编号'] }} · {{ evaluating['演练科目'] }} · 当前状态「{{ evaluating.status }}」
        </p>
        <label class="filter-item">
          <span>评估结论 *</span>
          <textarea
            v-model="evaluateForm['评估结论']"
            rows="3"
            placeholder="结论为空时不能标记完成，请填写本次演练的总体评估结论"
          ></textarea>
        </label>
        <label class="filter-item">
          <span>发现问题</span>
          <textarea
            v-model="evaluateForm['发现问题']"
            rows="3"
            placeholder="演练中暴露、需要后续整改的问题（没有可留空）"
          ></textarea>
        </label>
        <div class="form-actions">
          <button class="btn primary" type="submit">提交评估</button>
          <button class="btn ghost" type="button" @click="closeEvaluate">取消</button>
        </div>
      </form>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in visibleRows" :key="String(row.id)">
          <td>{{ row['演练编号'] ?? '—' }}</td>
          <td>{{ row['演练科目'] ?? '—' }}</td>
          <td>{{ row['参演单位'] ?? '—' }}</td>
          <td>{{ row['计划日期'] ?? '—' }}</td>
          <td>{{ row['组织人'] ?? '—' }}</td>
          <td>
            <span v-if="row['评估结论']" class="cell-clamp" :title="String(row['评估结论'])">{{ row['评估结论'] }}</span>
            <span v-else class="muted-text">待补录</span>
          </td>
          <td>
            <span v-if="row['发现问题']" class="cell-clamp issue-text" :title="String(row['发现问题'])">{{ row['发现问题'] }}</span>
            <span v-else>—</span>
          </td>
          <td><span class="status-tag" :class="statusClass(row.status)">{{ row.status }}</span></td>
          <td class="row-actions">
            <button v-if="row.status === '待实施'" class="link" type="button" @click="runAction('开始演练', row)">开始演练</button>
            <button v-if="row.status === '演练中'" class="link" type="button" @click="openEvaluate(row)">补录评估</button>
            <button v-if="row.status === '已评估'" class="link" type="button" @click="runAction('退回重新评估', row)">退回重新评估</button>
          </td>
        </tr>
        <tr v-if="!visibleRows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无符合条件的演练计划，可先登记一条演练计划</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条演练计划</span>
      <span v-if="successMessage" class="success-text">{{ successMessage }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | boolean | null>

const ENDPOINT = '/api/drill'
const columns = ["演练编号", "演练科目", "参演单位", "计划日期", "组织人", "评估结论", "发现问题", "演练状态"]
const statuses = ["待实施", "演练中", "已评估"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const successMessage = ref('')
const filters = ref<{ keyword: string; status: string }>({ keyword: '', status: '' })
const todoOnly = ref(false)

const creating = ref(false)
const createForm = ref<Record<string, string>>({ '演练科目': '', '参演单位': '', '计划日期': '', '组织人': '' })

const evaluating = ref<Row | null>(null)
const evaluateForm = ref<Record<string, string>>({ '评估结论': '', '发现问题': '' })

const visibleRows = computed(() =>
  todoOnly.value ? rows.value.filter((row) => row.pending === true) : rows.value,
)

const stats = computed(() => {
  const count = (status: string) => rows.value.filter((row) => row.status === status).length
  return [
    { label: '待实施', value: count('待实施') },
    { label: '演练中', value: count('演练中') },
    { label: '已评估', value: count('已评估') },
    { label: '待办清单', value: rows.value.filter((row) => row.pending === true).length },
  ]
})

function statusClass(status: unknown) {
  if (status === '已评估') return 'status-done'
  if (status === '演练中') return 'status-running'
  return 'status-todo'
}

function flashError(message: string) {
  successMessage.value = ''
  errorMessage.value = message
}

function flashSuccess(message: string) {
  errorMessage.value = ''
  successMessage.value = message
}

function resetFilters() {
  filters.value = { keyword: '', status: '' }
  todoOnly.value = false
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = ''
  successMessage.value = ''
  creating.value = true
}

function openEvaluate(row: Row) {
  errorMessage.value = ''
  successMessage.value = ''
  evaluating.value = row
  // 退回再评估时把上一版结论带出来，便于在原结论基础上修改。
  const conclusion = row['评估结论']
  const issues = row['发现问题']
  evaluateForm.value = {
    '评估结论': typeof conclusion === 'string' ? conclusion : '',
    '发现问题': typeof issues === 'string' ? issues : '',
  }
}

function closeEvaluate() {
  evaluating.value = null
}

async function submitCreate() {
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: createForm.value }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      // 登记失败：计划没有写入，表单内容保留，用户改完可再次提交。
      flashError(payload.message || '演练计划登记失败，请检查填写内容')
      return
    }
    creating.value = false
    createForm.value = { '演练科目': '', '参演单位': '', '计划日期': '', '组织人': '' }
    flashSuccess(payload.message || '演练计划已登记')
    await reload()
  } catch (error) {
    flashError(error instanceof Error ? error.message : '演练计划登记失败')
  }
}

async function submitEvaluate() {
  if (!evaluating.value) return
  const entryId = evaluating.value.id
  try {
    const response = await request(`${ENDPOINT}/${entryId}/actions`, {
      method: 'POST',
      body: JSON.stringify({
        values: { action: '提交评估', ...evaluateForm.value },
      }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      // 结论为空、重复评估等失败：弹层保持打开，清单刷新后该计划仍在待办清单。
      flashError(payload.message || '演练评估未生效')
      closeEvaluate()
      await reload()
      return
    }
    closeEvaluate()
    flashSuccess(payload.message || '演练评估已提交')
    await reload()
  } catch (error) {
    flashError(error instanceof Error ? error.message : '演练评估提交失败')
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      flashError(payload.message || '演练动作未生效，请稍后重试')
      await reload()
      return
    }
    flashSuccess(payload.message || `已执行「${action}」`)
    await reload()
  } catch (error) {
    flashError(error instanceof Error ? error.message : '演练操作失败')
  }
}

async function reload() {
  const params = new URLSearchParams()
  if (filters.value.keyword) params.set('keyword', filters.value.keyword)
  if (filters.value.status) params.set('status', filters.value.status)
  try {
    const response = await request(`${ENDPOINT}?${params.toString()}`)
    if (!response.ok) {
      throw new Error('演练计划列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    flashError(error instanceof Error ? error.message : '演练计划列表读取失败')
  }
}

onMounted(reload)
</script>
