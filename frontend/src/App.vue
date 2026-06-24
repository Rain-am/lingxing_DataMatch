<template>
  <main class="app-shell">
    <aside class="sidebar">
      <div>
        <h1>领星数仓表对数</h1>
        <p>按日期和店铺核对数仓与 ERP 汇总指标。</p>
      </div>
      <nav>
        <button :class="{ active: tab === 'rules' }" @click="tab = 'rules'">规则管理</button>
        <button :class="{ active: tab === 'run' }" @click="tab = 'run'">运行对账</button>
        <button :class="{ active: tab === 'result' }" @click="tab = 'result'" :disabled="!currentRun">结果查看</button>
      </nav>
    </aside>

    <section class="workspace">
      <div v-if="message" class="message" :class="messageType">{{ message }}</div>

      <section v-if="tab === 'rules'" class="panel">
        <div class="panel-header">
          <h2>规则管理</h2>
          <button class="secondary" @click="resetRuleForm">新建规则</button>
        </div>

        <div class="layout-two">
          <form class="form-grid" @submit.prevent="saveRule">
            <label>
              规则名称
              <input v-model="ruleForm.name" required placeholder="如：财务利润月度核对" />
            </label>
            <label>
              数仓表名
              <input v-model="ruleForm.warehouse_table" required placeholder="dw_profit_report" />
            </label>
            <label>
              数仓日期字段
              <input v-model="ruleForm.warehouse_date_field" required placeholder="biz_date" />
            </label>
            <label>
              数仓店铺字段
              <input v-model="ruleForm.warehouse_store_field" required placeholder="store_name" />
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
              <input v-model="ruleForm.erp_store_field" required placeholder="sellerName" />
            </label>

            <label class="wide">
              ERP 请求配置 JSON
              <textarea v-model="erpRequestConfigText" rows="8" spellcheck="false"></textarea>
            </label>

            <div class="metrics-editor">
              <div class="metrics-header">
                <h3>指标</h3>
                <button type="button" class="secondary" @click="addMetric">添加指标</button>
              </div>
              <div v-for="(metric, index) in ruleForm.metrics" :key="index" class="metric-row">
                <input v-model="metric.name" required placeholder="指标名" />
                <input v-model="metric.warehouse_expression" required placeholder="数仓表达式，如 profit_amount" />
                <input v-model="metric.erp_field" required placeholder="ERP字段，如 profitAmount" />
                <select v-model="metric.aggregation">
                  <option value="sum">sum</option>
                  <option value="count">count</option>
                </select>
                <input v-model.number="metric.tolerance" type="number" min="0" step="0.01" placeholder="容差" />
                <button type="button" class="icon-button danger" @click="removeMetric(index)" :disabled="ruleForm.metrics.length === 1">删</button>
              </div>
            </div>

            <div class="actions">
              <button type="submit">{{ editingRuleId ? '保存修改' : '创建规则' }}</button>
              <button type="button" class="secondary" @click="resetRuleForm">清空</button>
            </div>
          </form>

          <div class="rule-list">
            <h3>已保存规则</h3>
            <div v-if="rules.length === 0" class="empty">暂无规则</div>
            <article v-for="rule in rules" :key="rule.id" class="rule-card">
              <div>
                <strong>{{ rule.name }}</strong>
                <span>{{ rule.warehouse_table }} -> {{ rule.erp_module_path }}</span>
              </div>
              <div class="card-actions">
                <button class="secondary" @click="editRule(rule)">编辑</button>
                <button class="danger" @click="removeRule(rule.id)">删除</button>
              </div>
            </article>
          </div>
        </div>
      </section>

      <section v-if="tab === 'run'" class="panel">
        <div class="panel-header">
          <h2>运行对账</h2>
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

      <section v-if="tab === 'result'" class="panel">
        <div class="panel-header">
          <h2>结果查看</h2>
          <a v-if="currentRun" class="button-link" :href="exportRunUrl(currentRun.id)">导出 Excel</a>
        </div>

        <div v-if="currentRun" class="result-meta">
          <span>规则：{{ currentRun.rule_name }}</span>
          <span>日期：{{ currentRun.start_date }} 至 {{ currentRun.end_date }}</span>
          <span>粒度：{{ currentRun.granularity === 'day' ? '按天' : '按月' }}</span>
          <span>行数：{{ filteredRows.length }}</span>
        </div>

        <div class="filters">
          <input v-model="filters.store" placeholder="筛选店铺" />
          <input v-model="filters.period" placeholder="筛选周期" />
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
                <th>周期</th>
                <th>店铺</th>
                <th>指标</th>
                <th>数仓值</th>
                <th>ERP值</th>
                <th>差异值</th>
                <th>差异率</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in filteredRows" :key="`${row.period}-${row.store}-${row.metric}`" :class="row.status">
                <td>{{ row.period }}</td>
                <td>{{ row.store }}</td>
                <td>{{ row.metric }}</td>
                <td>{{ formatNumber(row.warehouse_value) }}</td>
                <td>{{ formatNumber(row.erp_value) }}</td>
                <td>{{ formatNumber(row.diff_value) }}</td>
                <td>{{ formatRate(row.diff_rate) }}</td>
                <td>{{ statusLabel(row.status) }}</td>
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
  granularity: 'day',
})
const filters = reactive({
  store: '',
  period: '',
  status: '',
})

const filteredRows = computed(() => {
  if (!currentRun.value) return []
  return currentRun.value.rows.filter((row) => {
    const storeOk = !filters.store || row.store.includes(filters.store)
    const periodOk = !filters.period || row.period.includes(filters.period)
    const statusOk = !filters.status || row.status === filters.status
    return storeOk && periodOk && statusOk
  })
})

function notify(text, type = 'info') {
  message.value = text
  messageType.value = type
  window.setTimeout(() => {
    if (message.value === text) message.value = ''
  }, 3500)
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
    notify('规则已删除', 'success')
  } catch (error) {
    notify(error.message, 'error')
  }
}

async function run() {
  running.value = true
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
