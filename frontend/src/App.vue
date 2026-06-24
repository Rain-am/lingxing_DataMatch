<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <h1>领星数仓对数</h1>
        <p>按月份汇总多个数仓与 ERP 来源，支持店铺下钻核对。</p>
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
              <input v-model="ruleForm.name" required placeholder="如：利润报表与订单利润对数" />
            </label>
            <label>
              基准来源
              <select v-model="ruleForm.comparison_base_source" required>
                <option v-for="source in ruleForm.sources" :key="source.name" :value="source.name">{{ source.name }}</option>
              </select>
            </label>
            <label>
              ERP 币种
              <input value="USD" disabled />
            </label>
          </div>

          <div class="sources-editor">
            <div class="section-head subtle">
              <h3>数据来源</h3>
              <div class="toolbar">
                <button type="button" class="secondary" @click="addSource('warehouse')">添加数仓来源</button>
                <button type="button" class="secondary" @click="addSource('erp')">添加 ERP 来源</button>
              </div>
            </div>

            <section v-for="(source, sourceIndex) in ruleForm.sources" :key="sourceIndex" class="source-block">
              <div class="section-head subtle">
                <h3>{{ source.name || '未命名来源' }}</h3>
                <button type="button" class="icon-button danger" :disabled="ruleForm.sources.length <= 2" @click="removeSource(sourceIndex)">删</button>
              </div>

              <div class="form-grid compact">
                <label>
                  来源名称
                  <input v-model="source.name" required @change="syncBaseSource" />
                </label>
                <label>
                  来源类型
                  <select v-model="source.type">
                    <option value="warehouse">数仓</option>
                    <option value="erp">ERP</option>
                  </select>
                </label>
                <label>
                  {{ source.type === 'warehouse' ? '数仓表名' : 'ERP API Path' }}
                  <input v-model="source.table_or_path" required />
                </label>
                <label>
                  {{ source.type === 'warehouse' ? '数仓日期字段' : 'ERP 返回日期字段' }}
                  <input v-model="source.date_field" :required="source.type === 'warehouse' || source.period_mode === 'response_field'" />
                </label>
                <label>
                  {{ source.type === 'warehouse' ? '数仓店铺字段' : 'ERP 返回店铺字段' }}
                  <input v-model="source.store_field" required />
                </label>
                <label v-if="source.type === 'erp'">
                  周期来源
                  <select v-model="source.period_mode">
                    <option value="response_field">返回日期字段</option>
                    <option value="request_month">请求月份</option>
                  </select>
                </label>
              </div>

              <label v-if="source.type === 'erp'" class="wide">
                ERP 请求配置 JSON（币种固定为 USD）
                <textarea v-model="source.request_config_text" rows="7" spellcheck="false"></textarea>
              </label>

              <div class="metrics-editor">
                <div class="section-head subtle">
                  <h3>指标</h3>
                  <button type="button" class="secondary" @click="addMetric(source)">添加指标</button>
                </div>
                <div class="metric-head">
                  <span>指标名</span>
                  <span>数仓表达式</span>
                  <span>ERP 字段</span>
                  <span>聚合</span>
                  <span>容差</span>
                  <span></span>
                </div>
                <div v-for="(metric, metricIndex) in source.metrics" :key="metricIndex" class="metric-row">
                  <input v-model="metric.name" required placeholder="毛利润" />
                  <input v-model="metric.warehouse_expression" :disabled="source.type === 'erp'" placeholder="grossProfit" />
                  <input v-model="metric.erp_field" :disabled="source.type === 'warehouse'" placeholder="grossProfit" />
                  <select v-model="metric.aggregation">
                    <option value="sum">sum</option>
                    <option value="count">count</option>
                  </select>
                  <input v-model.number="metric.tolerance" type="number" min="0" step="0.01" />
                  <button type="button" class="icon-button danger" :disabled="source.metrics.length === 1" @click="removeMetric(source, metricIndex)">删</button>
                </div>
              </div>
            </section>
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
                <th v-for="source in resultSources" :key="source" class="number">{{ source }}</th>
                <th v-for="source in diffSources" :key="`diff-${source}`" class="number">差异-{{ source }}</th>
                <th>状态</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <template v-for="row in filteredSummaryRows" :key="row.key">
                <tr class="summary-row" :class="row.status" @click="toggleExpand(row.key)">
                  <td>{{ row.period }}</td>
                  <td>{{ row.metric }}</td>
                  <td v-for="source in resultSources" :key="source" class="number">{{ formatNumber(row.values[source]) }}</td>
                  <td v-for="source in diffSources" :key="`diff-${source}`" class="number">{{ formatNumber(row.diffs[source]) }}</td>
                  <td>{{ statusLabel(row.status) }}</td>
                  <td class="drill-action">{{ expandedKey === row.key ? '收起' : '店铺明细' }}</td>
                </tr>
                <tr v-if="expandedKey === row.key" class="detail-row">
                  <td :colspan="4 + resultSources.length + diffSources.length">
                    <div class="detail-table">
                      <table>
                        <thead>
                          <tr>
                            <th>店铺</th>
                            <th v-for="source in resultSources" :key="source" class="number">{{ source }}</th>
                            <th v-for="source in diffSources" :key="`detail-diff-${source}`" class="number">差异-{{ source }}</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="detail in detailRows(row)" :key="`${row.key}-${detail.store}`">
                            <td>{{ detail.store || '-' }}</td>
                            <td v-for="source in resultSources" :key="source" class="number">{{ formatNumber(detail.values[source]) }}</td>
                            <td v-for="source in diffSources" :key="`detail-${source}`" class="number">{{ formatNumber(detail.diffs[source]) }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </td>
                </tr>
              </template>
              <tr v-if="filteredSummaryRows.length === 0">
                <td :colspan="4 + resultSources.length + diffSources.length" class="empty-table">暂无结果</td>
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

const defaultRequestConfig = (mode = 'page') => ({
  startDateParam: 'startDate',
  endDateParam: 'endDate',
  pageParam: mode === 'page' ? 'page' : '',
  pageSizeParam: mode === 'page' ? 'pageSize' : '',
  offsetParam: mode === 'offset' ? 'offset' : '',
  lengthParam: mode === 'offset' ? 'length' : '',
  paginationMode: mode,
  monthlyQueryParam: mode === 'page' ? 'monthlyQuery' : '',
  extraParams: {
    sids: [],
    mids: [],
    currencyCode: 'USD',
  },
})

const emptyMetric = (name = '') => ({
  name,
  warehouse_expression: '',
  erp_field: '',
  aggregation: 'sum',
  tolerance: 0,
})

const emptySource = (type = 'warehouse') => ({
  name: type === 'warehouse' ? '数仓' : 'ERP',
  type,
  table_or_path: '',
  date_field: type === 'warehouse' ? 'dataDate' : 'date',
  store_field: 'storeName',
  period_mode: 'response_field',
  request_config: type === 'erp' ? defaultRequestConfig() : {},
  request_config_text: type === 'erp' ? JSON.stringify(defaultRequestConfig(), null, 2) : '',
  metrics: [emptyMetric()],
})

const emptyRule = () => ({
  name: '',
  sources: [emptySource('warehouse'), emptySource('erp')],
  comparison_base_source: '数仓',
})

const tab = ref('rules')
const rules = ref([])
const currentRun = ref(null)
const running = ref(false)
const message = ref('')
const messageType = ref('info')
const editingRuleId = ref(null)
const ruleSearch = ref('')
const expandedKey = ref('')
const ruleForm = reactive(emptyRule())
const runForm = reactive({ rule_id: '', start_date: '', end_date: '', granularity: 'month' })
const filters = reactive({ period: '', metric: '', status: '' })

const filteredRules = computed(() => {
  const keyword = ruleSearch.value.trim().toLowerCase()
  if (!keyword) return rules.value
  return rules.value.filter((rule) => rule.name.toLowerCase().includes(keyword))
})

const summaryRows = computed(() => {
  const rows = currentRun.value?.summary_rows || []
  return rows
    .map((row) => ({ ...row, key: `${row.period}__${row.metric}` }))
    .sort((a, b) => a.period.localeCompare(b.period) || a.metric.localeCompare(b.metric, 'zh-CN'))
})

const resultSources = computed(() => {
  const names = new Set()
  for (const row of summaryRows.value) {
    for (const source of Object.keys(row.values || {})) names.add(source)
  }
  return Array.from(names)
})

const diffSources = computed(() => {
  const names = new Set()
  for (const row of summaryRows.value) {
    for (const source of Object.keys(row.diffs || {})) names.add(source)
  }
  return Array.from(names)
})

const filteredSummaryRows = computed(() => {
  return summaryRows.value.filter((row) => {
    return (!filters.period || row.period.includes(filters.period))
      && (!filters.metric || row.metric.includes(filters.metric))
      && (!filters.status || row.status === filters.status)
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

function hydrateSource(source) {
  const hydrated = {
    ...source,
    request_config: source.request_config || {},
    request_config_text: source.type === 'erp' ? JSON.stringify(forceUsd(source.request_config || defaultRequestConfig()), null, 2) : '',
    metrics: source.metrics?.length ? source.metrics : [emptyMetric()],
  }
  return hydrated
}

function normalizeRule(rule) {
  if (rule.sources?.length) {
    return {
      name: rule.name,
      sources: rule.sources.map(hydrateSource),
      comparison_base_source: rule.comparison_base_source || rule.sources[0].name,
    }
  }
  return {
    name: rule.name,
    comparison_base_source: '数仓',
    sources: [
      hydrateSource({
        name: '数仓',
        type: 'warehouse',
        table_or_path: rule.warehouse_table,
        date_field: rule.warehouse_date_field,
        store_field: rule.warehouse_store_field,
        period_mode: 'response_field',
        metrics: rule.metrics,
      }),
      hydrateSource({
        name: 'ERP',
        type: 'erp',
        table_or_path: rule.erp_module_path,
        date_field: rule.erp_date_field,
        store_field: rule.erp_store_field,
        period_mode: 'response_field',
        request_config: rule.erp_request_config,
        metrics: rule.metrics,
      }),
    ],
  }
}

function resetRuleForm() {
  Object.assign(ruleForm, emptyRule())
  editingRuleId.value = null
}

function editRule(rule) {
  Object.assign(ruleForm, normalizeRule(rule))
  editingRuleId.value = rule.id
  syncBaseSource()
}

function addSource(type) {
  const source = emptySource(type)
  let index = 1
  const baseName = source.name
  while (ruleForm.sources.some((item) => item.name === source.name)) {
    index += 1
    source.name = `${baseName}${index}`
  }
  ruleForm.sources.push(source)
  syncBaseSource()
}

function removeSource(index) {
  ruleForm.sources.splice(index, 1)
  syncBaseSource()
}

function addMetric(source) {
  source.metrics.push(emptyMetric())
}

function removeMetric(source, index) {
  source.metrics.splice(index, 1)
}

function syncBaseSource() {
  if (!ruleForm.sources.some((source) => source.name === ruleForm.comparison_base_source)) {
    ruleForm.comparison_base_source = ruleForm.sources[0]?.name || ''
  }
}

function forceUsd(config) {
  const next = JSON.parse(JSON.stringify(config || {}))
  next.extraParams = { ...(next.extraParams || {}), currencyCode: 'USD' }
  return next
}

function payloadFromForm() {
  const sources = ruleForm.sources.map((source) => {
    const requestConfig = source.type === 'erp' ? forceUsd(JSON.parse(source.request_config_text || '{}')) : {}
    return {
      name: source.name,
      type: source.type,
      table_or_path: source.table_or_path,
      date_field: source.period_mode === 'request_month' ? (source.date_field || '') : source.date_field,
      store_field: source.store_field,
      period_mode: source.type === 'erp' ? source.period_mode : 'response_field',
      request_config: requestConfig,
      metrics: source.metrics.map((metric) => ({
        name: metric.name,
        warehouse_expression: source.type === 'warehouse' ? metric.warehouse_expression : (metric.warehouse_expression || '*'),
        erp_field: source.type === 'erp' ? metric.erp_field : (metric.erp_field || metric.name),
        aggregation: metric.aggregation,
        tolerance: metric.tolerance || 0,
      })),
    }
  })
  return {
    name: ruleForm.name,
    sources,
    comparison_base_source: ruleForm.comparison_base_source || sources[0]?.name || '',
  }
}

async function saveRule() {
  try {
    const payload = payloadFromForm()
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

function detailRows(summary) {
  const rows = (currentRun.value?.rows || []).filter((row) => row.period === summary.period && row.metric === summary.metric)
  const baseSource = currentRuleBaseSource()
  const groups = new Map()
  for (const row of rows) {
    if (!groups.has(row.store)) groups.set(row.store, { store: row.store, values: {}, diffs: {} })
    groups.get(row.store).values[row.source] = Number(row.value || 0)
  }
  for (const group of groups.values()) {
    const baseValue = group.values[baseSource] || 0
    for (const source of diffSources.value) {
      group.diffs[source] = baseValue - (group.values[source] || 0)
    }
  }
  return Array.from(groups.values()).sort((a, b) => String(a.store).localeCompare(String(b.store), 'zh-CN'))
}

function currentRuleBaseSource() {
  const rule = rules.value.find((item) => item.id === currentRun.value?.rule_id)
  return rule?.comparison_base_source || resultSources.value[0] || ''
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN', { maximumFractionDigits: 4 })
}

function statusLabel(status) {
  return { matched: '一致', minor_diff: '轻微差异', major_diff: '异常差异' }[status] || status
}

onMounted(async () => {
  try {
    await refreshRules()
  } catch (error) {
    notify(error.message, 'error')
  }
})
</script>
