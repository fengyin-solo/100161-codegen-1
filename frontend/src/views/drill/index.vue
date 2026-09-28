<template>
  <section class="page" data-module="drill">
    <header class="page-head">
      <div>
        <h2>应急演练台账</h2>
        <p class="page-desc">登记演练计划，按“待实施 → 演练中 → 已评估”流转，并在演练结束后补录评估结论与发现问题。</p>
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
        <input v-model="filters.keyword" placeholder="演练科目 / 参演单位 / 组织人" />
      </label>
      <label class="filter-item">
        <span>计划状态</span>
        <select v-model="filters.status">
          <option value="">全部状态</option>
          <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <label class="check-item">
        <input v-model="pendingOnly" type="checkbox" />
        <span>只看待办清单</span>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table drill-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column" :class="{ 'wide-cell': wideColumns.includes(column) }">
            {{ displayValue(row, column) }}
          </td>
          <td class="row-actions">
            <button v-if="row.status === '待实施'" class="link" type="button" @click="startDrill(row)">
              开始演练
            </button>
            <button v-if="row.status === '演练中'" class="link" type="button" @click="openEvaluation(row)">
              补录评估
            </button>
            <button v-if="row.status === '已评估'" class="link" type="button" @click="openEvaluation(row)">
              变更评估
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无应急演练计划，可先登记一条演练计划</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条演练计划</span>
      <span v-if="infoMessage" class="info-text">{{ infoMessage }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <div v-if="showCreate" class="modal-mask" @click.self="closeCreate">
      <form class="modal-card" @submit.prevent="submitCreate">
        <h3>登记演练计划</h3>
        <label v-for="field in createFields" :key="field.name" class="form-item">
          <span>{{ field.label }}<em v-if="field.required">*</em></span>
          <component
            :is="field.type === 'date' ? 'input' : field.type"
            v-model="createForm[field.name]"
            :type="field.type === 'date' ? 'date' : field.type"
            :min="field.type === 'date' ? today : undefined"
            :placeholder="`请输入${field.label}`"
          />
        </label>
        <p v-if="createError" class="error-text modal-error">{{ createError }}</p>
        <div class="modal-actions">
          <button class="btn ghost" type="button" @click="closeCreate">取消</button>
          <button class="btn primary" type="submit">保存计划</button>
        </div>
      </form>
    </div>

    <div v-if="activeRow" class="modal-mask" @click.self="closeEvaluation()">
      <form class="modal-card" @submit.prevent="submitEvaluation">
        <h3>{{ evaluationAction === '提交评估' ? '补录演练评估' : '变更演练评估' }}</h3>
        <div class="detail-box">
          <span><strong>演练科目：</strong>{{ activeRow['演练科目'] }}</span>
          <span><strong>当前状态：</strong>{{ activeRow['计划状态'] }}</span>
        </div>
        <label class="form-item">
          <span>评估结论<em>*</em></span>
          <textarea v-model="evaluationForm['评估结论']" rows="4" placeholder="请填写演练评估结论"></textarea>
        </label>
        <label class="form-item">
          <span>发现问题</span>
          <textarea v-model="evaluationForm['发现问题']" rows="4" placeholder="可补充演练中发现的问题及整改建议"></textarea>
        </label>
        <p v-if="evaluationError" class="error-text modal-error">{{ evaluationError }}</p>
        <div class="modal-actions">
          <button class="btn ghost" type="button" @click="closeEvaluation()">取消</button>
          <button class="btn primary" type="submit">
            {{ evaluationAction === '提交评估' ? '标记完成' : '退回重新评估' }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { request } from '@/api/client'

type DrillStatus = '待实施' | '演练中' | '已评估'
type Row = Record<string, string | number | boolean | null>
type ActionResult = { ok: boolean; message: string; entry: Row | null }

const ENDPOINT = '/api/drill'
const columns = ['演练科目', '参演单位', '计划日期', '组织人', '评估结论', '发现问题', '计划状态']
const wideColumns = ['评估结论', '发现问题']
const statuses: DrillStatus[] = ['待实施', '演练中', '已评估']
const createFields = [
  { name: '演练科目', label: '演练科目', type: 'text', required: true },
  { name: '参演单位', label: '参演单位', type: 'text', required: true },
  { name: '计划日期', label: '计划日期', type: 'date', required: true },
  { name: '组织人', label: '组织人', type: 'text', required: true },
] as const

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const infoMessage = ref('')
const filters = reactive({ keyword: '', status: '' })
const pendingOnly = ref(false)

const showCreate = ref(false)
const createError = ref('')
const createForm = reactive<Record<string, string>>({
  演练科目: '',
  参演单位: '',
  计划日期: '',
  组织人: '',
})
const currentDate = new Date()
const today = [
  currentDate.getFullYear(),
  String(currentDate.getMonth() + 1).padStart(2, '0'),
  String(currentDate.getDate()).padStart(2, '0'),
].join('-')

const activeRow = ref<Row | null>(null)
const evaluationError = ref('')
const evaluationAction = ref<'提交评估' | '变更评估'>('提交评估')
const evaluationForm = reactive<Record<string, string>>({
  评估结论: '',
  发现问题: '',
})

const stats = computed(() => [
  { label: '待实施计划', value: rows.value.filter((row) => row.status === '待实施').length },
  { label: '演练中', value: rows.value.filter((row) => row.status === '演练中').length },
  { label: '已评估', value: rows.value.filter((row) => row.status === '已评估').length },
])

function displayValue(row: Row, column: string) {
  const value = row[column]
  return value === null || value === undefined || value === '' ? '—' : String(value)
}

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  pendingOnly.value = false
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  createError.value = ''
  showCreate.value = true
}

function closeCreate() {
  showCreate.value = false
}

function openEvaluation(row: Row) {
  activeRow.value = row
  evaluationAction.value = row.status === '已评估' ? '变更评估' : '提交评估'
  evaluationForm['评估结论'] = String(row['评估结论'] ?? '')
  evaluationForm['发现问题'] = String(row['发现问题'] ?? '')
  evaluationError.value = ''
}

function closeEvaluation(clearError = true) {
  activeRow.value = null
  if (clearError) evaluationError.value = ''
}

async function parseActionResponse(response: Response): Promise<ActionResult> {
  const payload = (await response.json()) as ActionResult
  if (!response.ok) throw new Error(payload.message || '操作未生效，请稍后重试')
  return payload
}

async function submitCreate() {
  createError.value = ''
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: { ...createForm } }),
    })
    const payload = await parseActionResponse(response)
    if (!payload.ok) {
      createError.value = payload.message
      return
    }
    showCreate.value = false
    Object.assign(createForm, { 演练科目: '', 参演单位: '', 计划日期: '', 组织人: '' })
    infoMessage.value = payload.message
    await reload()
  } catch (error) {
    createError.value = error instanceof Error ? error.message : '演练计划登记失败'
  }
}

async function startDrill(row: Row) {
  await runAction(row, { action: '开始演练' })
}

async function submitEvaluation() {
  if (!activeRow.value) return
  const row = activeRow.value
  const payloadValues = {
    action: evaluationAction.value,
    评估结论: evaluationForm['评估结论'],
    发现问题: evaluationForm['发现问题'],
  }
  await runAction(row, payloadValues, true)
}

async function runAction(row: Row, values: Record<string, string>, fromEvaluation = false) {
  errorMessage.value = ''
  infoMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values }),
    })
    const payload = await parseActionResponse(response)
    if (!payload.ok) {
      if (fromEvaluation) {
        evaluationError.value = payload.message
        closeEvaluation(false)
      }
      errorMessage.value = payload.message
      await reload()
      return
    }
    closeEvaluation()
    infoMessage.value = payload.message
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '应急演练操作失败'
    if (fromEvaluation) evaluationError.value = errorMessage.value
  }
}

async function reload() {
  errorMessage.value = ''
  const params = new URLSearchParams()
  if (filters.keyword.trim()) params.set('keyword', filters.keyword.trim())
  if (filters.status) params.set('status', filters.status)
  if (pendingOnly.value) params.set('pending_only', 'true')
  try {
    const response = await request(`${ENDPOINT}?${params.toString()}`)
    if (!response.ok) throw new Error('演练台账读取失败')
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '演练台账读取失败'
  }
}

onMounted(reload)
</script>
