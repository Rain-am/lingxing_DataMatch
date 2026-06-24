<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <h1>领星数仓对数</h1>
        <p>按周期汇总数仓与 ERP 指标，支持店铺下钻核对。</p>
      </div>
      <nav class="topnav">
        <button :class="{ active: tab === 'rules' }" @click="tab = 'rules'">规则管理</button>
        <button :class="{ active: tab === 'run' }" @click="tab = 'run'">运行对账</button>
        <button :class="{ active: tab === 'result' }" @click="tab = 'result'" :disabled="!currentRun">结果查看</button>
      </nav>
    </header>

    <section class="workspace">
      <div v-if="message" class="message" :class="messageType">{{ message }}</div>

      <section v-if="tab === 'rules'" class="panel rules-panel">
        <aside class="rules-index">
          <div class="section-head">
            <div>
              <h2>规则</h2>
              <span>{{ filteredRules.length }} / {{ rules.length }}</span>
            </div>
            <button class="secondary" @click="resetRuleForm">新建</button>
          </div>

          <input v-model="ruleSearch" class="search-input" placeholder="搜索规则名" />

          <div class="rule-list">
            <button
              v-for="rule in filteredRules"
              :key="rule.id"
              class="rule-name-item"
              :class="{ selected: editingRuleId === rule.id }"
              @click="editRule(rule)"
            >
              {{ rule.name }}
            </button>
            <div v-if="filteredRules.length === 0" class="empty">暂无规则</div>
          </div>
        </aside>

        <form class="rule-editor" @submit.prevent="saveRule">
          <div class="section-head">
            <div>
              <h2>{{ editingRuleId ? '编辑规则' : '新建规则' }}</h2>
              <span>{{ ruleForm.name || '未命名规则' }}</span>
            </div>
            <div class="toolbar">
              <button v-if="editingRuleId" type="button" class="danger" @click="removeRule(editingRuleId)">删除</button>
              <button type="button" class="secondary" @click="resetRuleForm">清空</button>
              <button type="submit">{{ editingRuleId ? '保存修改' : '创建规则' }}</button>
            </div>
          </div>

          <div class="form-grid compact">
            <label>
              规则名称
              <input v-model="ruleForm.name" required placeholder="如：利润报表月度对数" />
            </label>
            <label>
              数仓表名
              <input v-model="ruleForm.warehouse_table" required placeholder="bi_profit_statement_report_asin_usd" />
            </label>
            <label>
              数仓日期字段
              <input v-model="ruleForm.warehouse_date_field" required placeholder="dataDate" />
            </label>
            <label>
              数仓店铺字段
              <input v-model="ruleForm.warehouse_store_field" required placeholder="storeName" />
            </label>
            <label>
              ERP API Path
              <input v-model="ruleForm.erp_module_path" required placeholder="/bd/profit/report/open/report/seller/summary/list" />
            </label>
            <label>
              ERP 返回日期字段
              <input v-model="ruleForm.erp_date_field" required placeholder="date" />
            </label>
            <label>
              ERP 返回店铺字段
              <input v-model="ruleForm.erp_store_field" required placeholder="storeName" />
            </label>
          </div>

          <label class="wide">
            ERP 请求配置 JSON
            <textarea v-model="erpRequestConfigText" rows="8" spellcheck="false"></textarea>
          </label>

          <div class="metrics-editor">
            <div class="section-head subtle">
              <h3>指标</h3>
              <button type="button" class="secondary" @click="addMetric">添加指标</button>
            </div>
            <div class="metric-head">
              <span>指标名</span>
              <span>数仓表达式</span>
              <span>ERP 字段</span>
              <span>聚合</span>
              <span>容差</span>
              <span></span>
            </div>
            <div v-for="(metric, index) in ruleForm.metrics" :key="index" class="metric-row">
              <input v-model="metric.name" required placeholder="毛利润" />
              <input v-model="metric.warehouse_expression" required placeholder="grossProfit" />
              <input v-model="metric.erp_field" required placeholder="grossProfit" />
              <select v-model="metric.aggregation">
                <option value="sum">sum</option>
                <option value="count">count</option>
              </select>
              <input v-model.number="metric.tolerance" type="number" min="0" step="0.01" />
              <button type="button" class="icon-button danger" @click="removeMetric(index)" :disabled="ruleForm.metrics.length === 1">删</button>
            </div>
          </div>
        </form>
      </section>

      <section v-if="tab === 'run'" class="panel">
        <div class="section-head">
          <div>
            <h2>运行对账</h2>
            <span>选择规则和日期范围后开始核对</span>
          </div>
        </div>
        <form class="run-form" @submit.prevent="run">
          <label>
            选择规则
            <select v-model.number="runForm.rule_id" required>
              <option disabled value="">请选择</option>
              <option v-for="rule in rules" :key="rule.id" :value="rule.id">{{ rule.name }}</option>
            </select>
          </label>
          <label>
            开始日期
            <input v-model="runForm.start_date" type="date" required />
          </label>
          <label>
            结束日期
            <input v-model="runForm.end_date" type="date" required />
          </label>
          <label>
            汇总粒度
            <select v-model="runForm.granularity">
              <option value="day">按天</option>
              <option value="month">按月</option>
            </select>
          </label>
          <button :disabled="running">{{ running ? '运行中...' : '开始对账' }}</button>
        </form>
      </section>

      <section v-if="tab === 'result'" class="panel result-panel">
        <div class="section-head">
          <div>
            <h2>结果查看</h2>
            <span v-if="currentRun">{{ currentRun.rule_name }} · {{ currentRun.start_date }} 至 {{ currentRun.end_date }}</span>
          </div>
          <a v-if="currentRun" class="button-link" :href="exportRunUrl(currentRun.id)">导出 Excel</a>
        </div>

        <div v-if="currentRun" class="summary-strip">
          <div>
            <span>汇总行</span>
            <strong>{{ filteredSummaryRows.length }}</strong>
          </div>
          <div>
            <span>店铺明细</span>
            <strong>{{ currentRun.rows.length }}</strong>
          </div>
          <div>
            <span>状态</span>
            <strong>{{ runStatusLabel }}</strong>
          </div>
        </div>

        <div class="filters">
          <input v-model="filters.period" placeholder="筛选月份" />
          <input v-model="filters.metric" placeholder="筛选指标" />
          <select v-model="filters.status">
            <option value="">全部状态</option>
            <option value="matched">一致</option>
            <option value="minor_diff">轻微差异</option>
            <option value="major_diff">异常差异</option>
          </select>
        </div>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>月份</th>
                <th>指标</th>
                <th class="number">数仓合计</th>
                <th class="number">ERP 合计</th>
                <th class="number">差异值</th>
                <th class="number">差异率</th>
                <th>状态</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <template v-for="row in filteredSummaryRows" :key="row.key">
                <tr class="summary-row" :class="row.status" @click="toggleExpand(row.key)">
                  <td>{{ row.period }}</td>
                  <td>{{ row.metric }}</td>
                  <td class="number">{{ formatNumber(row.warehouse_value) }}</td>
                  <td class="number">{{ formatNumber(row.erp_value) }}</td>
                  <td class="number">{{ formatNumber(row.diff_value) }}</td>
                  <td class="number">{{ formatRate(row.diff_rate) }}</td>
                  <td>{{ statusLabel(row.status) }}</td>
                  <td class="drill-action">{{ expandedKey === row.key ? '收起' : '店铺明细' }}</td>
                </tr>
                <tr v-if="expandedKey === row.key" class="detail-row">
                  <td colspan="8">
                    <div class="detail-table">
                      <table>
                        <thead>
                          <tr>
                            <th>店铺</th>
                            <th class="number">数仓值</th>
                            <th class="number">ERP 值</th>
                            <th class="number">差异值</th>
                            <th class="number">差异率</th>
                            <th>状态</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="detail in row.details" :key="`${row.key}-${detail.store}`" :class="detail.status">
                            <td>{{ detail.store || '-' }}</td>
                            <td class="number">{{ formatNumber(detail.warehouse_value) }}</td>
                            <td class="number">{{ formatNumber(detail.erp_value) }}</td>
                            <td class="number">{{ formatNumber(detail.diff_value) }}</td>
                            <td class="number">{{ formatRate(detail.diff_rate) }}</td>
                            <td>{{ statusLabel(detail.status) }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </td>
                </tr>
              </template>
              <tr v-if="filteredSummaryRows.length === 0">
                <td colspan="8" class="empty-table">暂无结果</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { createRule, deleteRule, exportRunUrl, listRules, runReconcile, updateRule } from './api'

const defaultRequestConfig = () => ({
  startDateParam: 'startDate',
  endDateParam: 'endDate',
  pageParam: 'page',
  pageSizeParam: 'pageSize',
  monthlyQueryParam: 'monthlyQuery',
  extraParams: {
    sids: [],
    mids: [],
    currencyCode: 'CNY',
  },
})

const tab = ref('rules')
const rules = ref([])
const currentRun = ref(null)
const running = ref(false)
const message = ref('')
const messageType = ref('info')
const editingRuleId = ref(null)
const erpRequestConfigText = ref(JSON.stringify(defaultRequestConfig(), null, 2))
const ruleSearch = ref('')
const expandedKey = ref('')

const emptyMetric = () => ({
  name: '',
  warehouse_expression: '',
  erp_field: '',
  aggregation: 'sum',
  tolerance: 0,
})

const emptyRule = () => ({
  name: '',
  warehouse_table: '',
  warehouse_date_field: '',
  warehouse_store_field: '',
  erp_module_path: '',
  erp_date_field: '',
  erp_store_field: '',
  erp_request_config: defaultRequestConfig(),
  metrics: [emptyMetric()],
})

const ruleForm = reactive(emptyRule())
const runForm = reactive({
  rule_id: '',
  start_date: '',
  end_date: '',
  granularity: 'month',
})
const filters = reactive({
  period: '',
  metric: '',
  status: '',
})

const filteredRules = computed(() => {
  const keyword = ruleSearch.value.trim().toLowerCase()
  if (!keyword) return rules.value
  return rules.value.filter((rule) => rule.name.toLowerCase().includes(keyword))
})

const summaryRows = computed(() => {
  if (!currentRun.value) return []
  const severity = { matched: 0, minor_diff: 1, major_diff: 2 }
  const labelBySeverity = ['matched', 'minor_diff', 'major_diff']
  const groups = new Map()

  for (const row of currentRun.value.rows) {
    const key = `${row.period}__${row.metric}`
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        period: row.period,
        metric: row.metric,
        warehouse_value: 0,
        erp_value: 0,
        diff_value: 0,
        status_score: 0,
        details: [],
      })
    }
    const group = groups.get(key)
    group.warehouse_value += Number(row.warehouse_value || 0)
    group.erp_value += Number(row.erp_value || 0)
    group.diff_value += Number(row.diff_value || 0)
    group.status_score = Math.max(group.status_score, severity[row.status] ?? 0)
    group.details.push(row)
  }

  return Array.from(groups.values())
    .map((row) => ({
      ...row,
      diff_rate: row.erp_value === 0 ? null : row.diff_value / row.erp_value,
      status: labelBySeverity[row.status_score] || 'matched',
      details: [...row.details].sort((a, b) => String(a.store).localeCompare(String(b.store), 'zh-CN')),
    }))
    .sort((a, b) => a.period.localeCompare(b.period) || a.metric.localeCompare(b.metric, 'zh-CN'))
})

const filteredSummaryRows = computed(() => {
  return summaryRows.value.filter((row) => {
    const periodOk = !filters.period || row.period.includes(filters.period)
    const metricOk = !filters.metric || row.metric.includes(filters.metric)
    const statusOk = !filters.status || row.status === filters.status
    return periodOk && metricOk && statusOk
  })
})

const runStatusLabel = computed(() => {
  if (!currentRun.value) return '-'
  if (summaryRows.value.some((row) => row.status === 'major_diff')) return '存在异常差异'
  if (summaryRows.value.some((row) => row.status === 'minor_diff')) return '存在轻微差异'
  return '一致'
})

function notify(text, type = 'info') {
  message.value = text
  messageType.value = type
  window.setTimeout(() => {
    if (message.value === text) message.value = ''
  }, 4500)
}

async function refreshRules() {
  rules.value = await listRules()
  if (!runForm.rule_id && rules.value.length > 0) runForm.rule_id = rules.value[0].id
}

function resetRuleForm() {
  Object.assign(ruleForm, emptyRule())
  erpRequestConfigText.value = JSON.stringify(ruleForm.erp_request_config, null, 2)
  editingRuleId.value = null
}

function editRule(rule) {
  Object.assign(ruleForm, JSON.parse(JSON.stringify(rule)))
  if (!ruleForm.erp_request_config || Object.keys(ruleForm.erp_request_config).length === 0) {
    ruleForm.erp_request_config = defaultRequestConfig()
  }
  erpRequestConfigText.value = JSON.stringify(ruleForm.erp_request_config, null, 2)
  editingRuleId.value = rule.id
}

function addMetric() {
  ruleForm.metrics.push(emptyMetric())
}

function removeMetric(index) {
  ruleForm.metrics.splice(index, 1)
}

async function saveRule() {
  try {
    const requestConfig = JSON.parse(erpRequestConfigText.value)
    const payload = JSON.parse(JSON.stringify(ruleForm))
    payload.erp_request_config = requestConfig
    if (editingRuleId.value) {
      await updateRule(editingRuleId.value, payload)
      notify('规则已更新', 'success')
    } else {
      await createRule(payload)
      notify('规则已创建', 'success')
    }
    resetRuleForm()
    await refreshRules()
  } catch (error) {
    notify(`保存失败：${error.message}`, 'error')
  }
}

async function removeRule(id) {
  if (!window.confirm('确认删除这条规则？')) return
  try {
    await deleteRule(id)
    await refreshRules()
    resetRuleForm()
    notify('规则已删除', 'success')
  } catch (error) {
    notify(error.message, 'error')
  }
}

async function run() {
  running.value = true
  expandedKey.value = ''
  try {
    currentRun.value = await runReconcile(runForm)
    tab.value = 'result'
    notify('对账完成', 'success')
  } catch (error) {
    notify(error.message, 'error')
  } finally {
    running.value = false
  }
}

function toggleExpand(key) {
  expandedKey.value = expandedKey.value === key ? '' : key
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN', { maximumFractionDigits: 4 })
}

function formatRate(value) {
  if (value === null || value === undefined) return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function statusLabel(status) {
  return {
    matched: '一致',
    minor_diff: '轻微差异',
    major_diff: '异常差异',
  }[status] || status
}

onMounted(async () => {
  try {
    await refreshRules()
  } catch (error) {
    notify(error.message, 'error')
  }
})
</script>
