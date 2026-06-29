<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <h1>领星数仓对数</h1>
        <p>规则独立运行，结果自由组合对比，支持店铺 ID 映射。</p>
      </div>
      <nav class="topnav">
        <button :class="{ active: tab === 'rules' }" @click="tab = 'rules'">规则管理</button>
        <button :class="{ active: tab === 'run' }" @click="tab = 'run'">运行对账</button>
        <button :class="{ active: tab === 'result' }" @click="openResults">结果查看</button>
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
              <strong>{{ rule.name }}</strong>
              <span>{{ rule.updated_at ? formatDateTime(rule.updated_at) : '未更新' }}</span>
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

          <section class="form-section">
            <h3>基础信息</h3>
            <div class="form-grid compact">
              <label>
                规则名称
                <input v-model="ruleForm.name" required placeholder="如：订单利润月度对数" />
              </label>
              <label>
                ERP 币种
                <input value="USD" disabled />
              </label>
            </div>
          </section>

          <section class="form-section">
            <h3>数仓配置</h3>
            <div class="form-grid compact">
              <label>
                数仓表名
                <input v-model="ruleForm.warehouse_table" required placeholder="bi_order_profit_msku_info_usd" />
              </label>
              <label>
                数仓日期字段
                <input v-model="ruleForm.warehouse_date_field" required placeholder="r_date" />
              </label>
              <label>
                数仓店铺字段
                <input v-model="ruleForm.warehouse_store_field" required placeholder="seller_id 或 seller_name" />
              </label>
            </div>
            <StoreMappingForm v-model="ruleForm.warehouse_store_mapping" title="数仓店铺映射" />
          </section>

          <section class="form-section">
            <h3>ERP 配置</h3>
            <p class="hint">
              订单利润接口没有返回日期字段时，周期来源选“请求月份”，ERP 返回日期字段会自动忽略。ERP 返回店铺字段支持普通字段和路径字段，例如 sid、data>>sids。
            </p>
            <div v-if="orderProfitStoreFieldWarning" class="inline-warning">
              文档里的请求参数 sids 不是返回字段；如果返回字段写作 data&gt;&gt;sids，请在这里填 data&gt;&gt;sids。
            </div>
            <div class="form-grid compact">
              <label>
                ERP API Path
                <input v-model="ruleForm.erp_module_path" required placeholder="/basicOpen/finance/mreport/OrderProfit" />
              </label>
              <label>
                ERP 返回日期字段
                <input
                  v-model="ruleForm.erp_date_field"
                  :disabled="ruleForm.erp_period_mode === 'request_month'"
                  :required="ruleForm.erp_period_mode === 'response_field'"
                  :placeholder="ruleForm.erp_period_mode === 'request_month' ? '无需填写' : 'date'"
                />
              </label>
              <label>
                ERP 返回店铺字段
                <input v-model="ruleForm.erp_store_field" required placeholder="sid、storeName 或 data>>sids" />
              </label>
              <label>
                周期来源
                <select v-model="ruleForm.erp_period_mode">
                  <option value="response_field">返回日期字段</option>
                  <option value="request_month">请求月份</option>
                </select>
              </label>
            </div>
            <StoreMappingForm v-model="ruleForm.erp_store_mapping" title="ERP 店铺映射" />
            <label class="wide">
              ERP 请求配置 JSON（币种固定为 USD）
              <textarea v-model="erpRequestConfigText" rows="7" spellcheck="false"></textarea>
            </label>
          </section>

          <section class="form-section">
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
              <input v-model="metric.warehouse_expression" required placeholder="gross_profit" />
              <input v-model="metric.erp_field" required placeholder="gross_profit 或 data>>gross_profit" />
              <select v-model="metric.aggregation">
                <option value="sum">sum</option>
                <option value="count">count</option>
              </select>
              <input v-model.number="metric.tolerance" type="number" min="0" step="0.01" />
              <button type="button" class="icon-button danger" :disabled="ruleForm.metrics.length === 1" @click="removeMetric(index)">删</button>
            </div>
          </section>
        </form>
      </section>

      <section v-if="tab === 'run'" class="panel run-panel">
        <div class="section-head">
          <div>
            <h2>运行对账</h2>
            <span>可一次选择多个规则，同一日期范围批量运行。</span>
          </div>
        </div>
        <form class="run-form batch" @submit.prevent="runBatch">
          <label class="date-preset-field">
            日期范围
            <span class="date-presets">
              <button
                v-for="option in datePresetOptions"
                :key="option.value"
                type="button"
                class="secondary"
                :class="{ active: datePreset === option.value }"
                @click="applyDatePreset(option.value)"
              >
                {{ option.label }}
              </button>
            </span>
          </label>
          <label>
            开始日期
            <input v-model="runForm.start_date" type="date" required @input="markCustomDateRange" />
          </label>
          <label>
            结束日期
            <input v-model="runForm.end_date" type="date" required @input="markCustomDateRange" />
          </label>
          <label>
            汇总粒度
            <select v-model="runForm.granularity">
              <option value="day">按天</option>
              <option value="month">按月</option>
            </select>
          </label>
          <button :disabled="running || selectedRuleIds.length === 0">
            {{ running ? runButtonText : `开始对账（${selectedRuleIds.length}）` }}
          </button>
        </form>
        <div v-if="currentJob" class="job-progress">
          <div class="job-progress-head">
            <strong>{{ jobStatusLabel }}</strong>
            <span>{{ currentJob.progress_percent || 0 }}%</span>
          </div>
          <progress :value="currentJob.progress_percent || 0" max="100"></progress>
          <div class="job-progress-meta">
            <span v-if="currentJob.current_rule_name">规则：{{ currentJob.current_rule_name }}</span>
            <span v-if="currentJob.stage">阶段：{{ currentJob.stage }}</span>
            <span v-if="currentJob.detail">明细：{{ currentJob.detail }}</span>
            <span v-if="currentJob.total_steps">{{ currentJob.done_steps }} / {{ currentJob.total_steps }} 步</span>
          </div>
          <p v-if="currentJob.status !== 'completed' && !currentJob.stage">
            任务已提交，页面会自动刷新进度。
          </p>
        </div>
        <div v-if="failedRuns.length" class="failure-list">
          <div v-for="failure in failedRuns" :key="failure.run?.id || failure.rule_id" class="failure-item">
            <div>
              <strong>{{ failure.rule_name || `规则 ${failure.rule_id}` }}</strong>
              <span v-if="failure.run">#{{ failure.run.id }}</span>
            </div>
            <p>{{ failure.error_message }}</p>
            <button v-if="failure.run" type="button" class="secondary" @click="selectRun(failure.run)">查看该失败记录</button>
          </div>
        </div>
        <div class="selected-rule-bar">
          <strong>已勾选规则：{{ selectedRuleIds.length }}</strong>
          <button v-if="running" type="button" class="danger compact-danger" :disabled="cancelling" @click="cancelCurrentJob">
            {{ cancelling ? '取消中...' : '取消对账' }}
          </button>
        </div>
        <div class="check-list">
          <label v-for="rule in rules" :key="rule.id" class="check-item">
            <input v-model="selectedRuleIds" type="checkbox" :value="rule.id" />
            <span>{{ rule.name }}</span>
          </label>
        </div>
      </section>

      <section v-if="tab === 'result'" class="panel result-panel">
        <div class="section-head">
          <div>
            <h2>结果查看</h2>
            <span>选择多个运行结果，按月份、指标、规则自由对比。</span>
          </div>
          <button class="secondary" :disabled="selectedRunIds.length === 0" @click="downloadCompare">导出所选对比</button>
        </div>

        <div class="result-layout">
          <aside class="run-picker">
            <div class="section-head subtle">
              <h3>运行结果</h3>
              <button class="secondary" @click="refreshRuns">刷新</button>
            </div>
            <div class="filters stacked">
              <select v-model="runFilters.rule_id" @change="refreshRuns">
                <option value="">全部规则</option>
                <option v-for="rule in rules" :key="rule.id" :value="rule.id">{{ rule.name }}</option>
              </select>
              <select v-model="runFilters.status" @change="refreshRuns">
                <option value="">全部状态</option>
                <option value="success">成功</option>
                <option value="failed">失败</option>
              </select>
            </div>
            <div class="run-list">
              <div v-for="run in runHistory" :key="run.id" class="run-item">
                <label class="run-select">
                  <input v-model="selectedRunIds" type="checkbox" :value="run.id" @change="syncSelectedRuns" />
                  <span>
                    <strong>{{ run.rule_name }} #{{ run.id }}</strong>
                    <small>{{ run.start_date }} 至 {{ run.end_date }} · {{ run.status }}</small>
                    <small v-if="run.error_message" class="run-error">{{ run.error_message }}</small>
                  </span>
                </label>
                <button type="button" class="icon-button danger" @click="removeRun(run)">删</button>
              </div>
              <div v-if="runHistory.length === 0" class="empty">暂无运行记录</div>
            </div>
          </aside>

          <section class="compare-area" @click="closeFilterMenu">
            <div class="summary-strip">
              <div>
                <span>已选结果</span>
                <strong>{{ selectedRuns.length }}</strong>
              </div>
              <div>
                <span>汇总行</span>
                <strong>{{ filteredCompareRows.length }}</strong>
              </div>
              <div>
                <span>店铺明细</span>
                <strong>{{ selectedRuns.reduce((sum, run) => sum + (run.rows?.length || 0), 0) }}</strong>
              </div>
            </div>
            <div class="filters">
              <div class="dropdown-filter">
                <button type="button" class="filter-button" @click.stop="toggleFilterMenu('period')">
                  <span>月份</span>
                  <strong>{{ periodFilterLabel }}</strong>
                </button>
                <div v-if="openFilterMenu === 'period'" class="filter-menu" @click.stop>
                  <button type="button" class="filter-menu-option all-option" @click="clearFilter('periods')">
                    全部月份
                  </button>
                  <label v-for="period in availablePeriods" :key="period" class="filter-menu-option">
                    <input
                      type="checkbox"
                      :checked="compareFilters.periods.includes(period)"
                      @change="toggleFilterValue('periods', period)"
                    />
                    <span>{{ period }}</span>
                  </label>
                </div>
              </div>
              <div class="dropdown-filter">
                <button type="button" class="filter-button" @click.stop="toggleFilterMenu('metric')">
                  <span>指标</span>
                  <strong>{{ metricFilterLabel }}</strong>
                </button>
                <div v-if="openFilterMenu === 'metric'" class="filter-menu" @click.stop>
                  <button type="button" class="filter-menu-option all-option" @click="clearFilter('metrics')">
                    全部指标
                  </button>
                  <label v-for="metric in availableMetrics" :key="metric" class="filter-menu-option">
                    <input
                      type="checkbox"
                      :checked="compareFilters.metrics.includes(metric)"
                      @change="toggleFilterValue('metrics', metric)"
                    />
                    <span>{{ metric }}</span>
                  </label>
                </div>
              </div>
              <input v-model="compareFilters.rule" placeholder="筛选规则名" />
            </div>
            <div v-if="selectedRunsWithoutSummary.length" class="inline-warning">
              {{ selectedRunsWithoutSummary.map((run) => `${run.rule_name} #${run.id}`).join('、') }} 无汇总数据，请重新运行该规则后再查看。
            </div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>月份</th>
                    <th>指标</th>
                    <th class="number">数仓</th>
                    <th class="number">ERP</th>
                    <th class="number">差异</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <template v-for="row in filteredCompareRows" :key="row.key">
                    <tr class="summary-row" @click="toggleExpand(row.key)">
                      <td>{{ row.period }}</td>
                      <td>{{ row.metric }}</td>
                      <td class="number">{{ formatNumber(row.warehouse) }}</td>
                      <td class="number">{{ formatNumber(row.erp) }}</td>
                      <td class="number">{{ formatNumber(row.diff) }}</td>
                      <td class="drill-action">{{ expandedKey === row.key ? '收起' : '店铺明细' }}</td>
                    </tr>
                    <tr v-if="expandedKey === row.key" class="detail-row">
                      <td colspan="6">
                        <div class="detail-table">
                          <table>
                            <thead>
                              <tr>
                                <th>店铺</th>
                                <th class="number">数仓</th>
                                <th class="number">ERP</th>
                                <th class="number">差异</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="detail in detailRows(row)" :key="`${row.key}-${detail.store}`">
                                <td>{{ detail.store || '-' }}</td>
                                <td class="number">{{ formatNumber(detail.warehouse) }}</td>
                                <td class="number">{{ formatNumber(detail.erp) }}</td>
                                <td class="number">{{ formatNumber(detail.diff) }}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </td>
                    </tr>
                  </template>
                  <tr v-if="filteredCompareRows.length === 0">
                    <td colspan="6" class="empty-table">请选择运行结果，或调整筛选条件</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  cancelBatchRunJob,
  createRule,
  deleteRule,
  deleteRun,
  exportCompareRuns,
  getBatchRunJob,
  getRun,
  listRules,
  listRuns,
  startBatchRunJob,
  updateRule,
} from './api'

const StoreMappingForm = defineComponent({
  props: {
    modelValue: { type: Object, required: true },
    title: { type: String, required: true },
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const patch = (updates) => emit('update:modelValue', { ...props.modelValue, ...updates })
    return () => h('div', { class: 'mapping-box' }, [
      h('label', { class: 'check-inline' }, [
        h('input', {
          type: 'checkbox',
          checked: Boolean(props.modelValue.enabled),
          onChange: (event) => patch({ enabled: event.target.checked }),
        }),
        h('span', props.title),
      ]),
      props.modelValue.enabled
        ? h('div', { class: 'form-grid compact' }, [
            h('label', ['映射表', h('input', {
              value: props.modelValue.table,
              placeholder: 'seller',
              onInput: (event) => patch({ table: event.target.value }),
            })]),
            h('label', ['ID 字段', h('input', {
              value: props.modelValue.id_field,
              placeholder: 'sid',
              onInput: (event) => patch({ id_field: event.target.value }),
            })]),
            h('label', ['名称字段', h('input', {
              value: props.modelValue.name_field,
              placeholder: 'name',
              onInput: (event) => patch({ name_field: event.target.value }),
            })]),
          ])
        : null,
    ])
  },
})

const defaultRequestConfig = (mode = 'page') => ({
  startDateParam: 'startDate',
  endDateParam: 'endDate',
  pageParam: mode === 'page' ? 'page' : '',
  pageSizeParam: mode === 'page' ? 'pageSize' : '',
  offsetParam: mode === 'offset' ? 'offset' : '',
  lengthParam: mode === 'offset' ? 'length' : '',
  paginationMode: mode,
  monthlyQueryParam: mode === 'page' ? 'monthlyQuery' : '',
  extraParams: { sids: [], mids: [], currencyCode: 'USD' },
})

const defaultStoreMapping = () => ({ enabled: false, table: 'seller', id_field: 'sid', name_field: 'name' })
const emptyMetric = () => ({ name: '', warehouse_expression: '', erp_field: '', aggregation: 'sum', tolerance: 0 })
const emptyRule = () => ({
  name: '',
  warehouse_table: '',
  warehouse_date_field: 'dataDate',
  warehouse_store_field: 'storeName',
  warehouse_store_mapping: defaultStoreMapping(),
  erp_module_path: '',
  erp_date_field: 'date',
  erp_store_field: 'storeName',
  erp_period_mode: 'response_field',
  erp_store_mapping: defaultStoreMapping(),
  metrics: [emptyMetric()],
})

const tab = ref('rules')
const rules = ref([])
const runHistory = ref([])
const selectedRuns = ref([])
const selectedRuleIds = ref([])
const selectedRunIds = ref([])
const failedRuns = ref([])
const running = ref(false)
const cancelling = ref(false)
const currentJob = ref(null)
const jobPollTimer = ref(null)
const message = ref('')
const messageType = ref('info')
const editingRuleId = ref(null)
const ruleSearch = ref('')
const expandedKey = ref('')
const openFilterMenu = ref('')
const erpRequestConfigText = ref(JSON.stringify(defaultRequestConfig(), null, 2))
const ruleForm = reactive(emptyRule())
const runForm = reactive({ start_date: '', end_date: '', granularity: 'month' })
const datePreset = ref('custom')
const datePresetOptions = [
  { value: 'current_month', label: '本月' },
  { value: 'previous_month', label: '上月' },
  { value: 'recent_three_months', label: '近3个月' },
  { value: 'custom', label: '自定义' },
]
const runFilters = reactive({ rule_id: '', status: '' })
const compareFilters = reactive({ periods: [], metrics: [], rule: '' })

const filteredRules = computed(() => {
  const keyword = ruleSearch.value.trim().toLowerCase()
  return keyword ? rules.value.filter((rule) => rule.name.toLowerCase().includes(keyword)) : rules.value
})

const orderProfitStoreFieldWarning = computed(() => {
  return ruleForm.erp_module_path.toLowerCase().includes('orderprofit') && ruleForm.erp_store_field.trim() === 'sids'
})

const runButtonText = computed(() => {
  if (!currentJob.value) return '运行中...'
  const percent = currentJob.value.progress_percent
  return Number.isFinite(percent) ? `运行中 ${percent}%` : '运行中...'
})

const jobStatusLabel = computed(() => {
  if (!currentJob.value) return '后台运行中'
  if (currentJob.value.status === 'completed') return '运行完成'
  if (currentJob.value.status === 'cancelled') return '已取消'
  if (currentJob.value.status === 'cancel_requested') return '取消中'
  return '后台运行中'
})

const compareRows = computed(() => {
  const groups = new Map()
  for (const run of selectedRuns.value) {
    for (const row of run.summary_rows || []) {
      const period = formatPeriodMonth(row.period)
      const key = `${period}__${row.metric}`
      if (!groups.has(key)) groups.set(key, { key, period, metric: row.metric, warehouse: 0, erp: 0, diff: 0 })
      const group = groups.get(key)
      const values = sourceAmounts(row)
      group.warehouse += values.warehouse
      group.erp += values.erp
      group.diff += values.diff
    }
  }
  return Array.from(groups.values()).sort((a, b) => a.period.localeCompare(b.period) || a.metric.localeCompare(b.metric, 'zh-CN'))
})

const availablePeriods = computed(() => {
  const periods = new Set()
  for (const run of selectedRuns.value) {
    for (const row of run.summary_rows || []) {
      periods.add(formatPeriodMonth(row.period))
    }
  }
  return Array.from(periods).sort()
})

const availableMetrics = computed(() => {
  const metrics = new Set()
  for (const run of selectedRuns.value) {
    for (const row of run.summary_rows || []) {
      metrics.add(row.metric)
    }
  }
  return Array.from(metrics).sort((a, b) => a.localeCompare(b, 'zh-CN'))
})

const selectedRunsWithoutSummary = computed(() => {
  return selectedRuns.value.filter((run) => run.status === 'success' && !(run.summary_rows || []).length)
})

const periodFilterLabel = computed(() => filterLabel(compareFilters.periods, '全部月份', '月份'))
const metricFilterLabel = computed(() => filterLabel(compareFilters.metrics, '全部指标', '指标'))

const filteredCompareRows = computed(() => {
  const ruleKeyword = compareFilters.rule.trim().toLowerCase()
  const allowedRuleNames = ruleKeyword
    ? new Set(selectedRuns.value.filter((run) => run.rule_name.toLowerCase().includes(ruleKeyword)).map((run) => run.rule_name))
    : null
  const rows = allowedRuleNames ? buildCompareRows(allowedRuleNames) : compareRows.value
  return rows
    .filter((row) => {
      return (!compareFilters.periods.length || compareFilters.periods.includes(row.period))
        && (!compareFilters.metrics.length || compareFilters.metrics.includes(row.metric))
    })
})

watch(availablePeriods, (periods) => {
  compareFilters.periods = compareFilters.periods.filter((period) => periods.includes(period))
})

watch(availableMetrics, (metrics) => {
  compareFilters.metrics = compareFilters.metrics.filter((metric) => metrics.includes(metric))
})

watch(selectedRuns, () => {
  openFilterMenu.value = ''
})

watch(() => ruleForm.erp_period_mode, (mode) => {
  if (mode === 'request_month') ruleForm.erp_date_field = ''
  if (mode === 'response_field' && !ruleForm.erp_date_field) ruleForm.erp_date_field = 'date'
})

watch(tab, (nextTab) => {
  if (nextTab === 'run') ensureRunDateDefaults()
}, { immediate: true })

function notify(text, type = 'info') {
  message.value = text
  messageType.value = type
  window.setTimeout(() => {
    if (message.value === text) message.value = ''
  }, 5000)
}

function ensureRunDateDefaults() {
  if (!runForm.start_date || !runForm.end_date) applyDatePreset('current_month')
}

function applyDatePreset(preset) {
  datePreset.value = preset
  if (preset === 'custom') return
  const range = dateRangeForPreset(preset)
  runForm.start_date = formatDateInput(range.start)
  runForm.end_date = formatDateInput(range.end)
}

function markCustomDateRange() {
  datePreset.value = 'custom'
}

function dateRangeForPreset(preset) {
  if (preset === 'previous_month') return monthRange(-1)
  if (preset === 'recent_three_months') {
    const now = new Date()
    return {
      start: new Date(now.getFullYear(), now.getMonth() - 2, 1),
      end: new Date(now.getFullYear(), now.getMonth() + 1, 0),
    }
  }
  return monthRange(0)
}

function monthRange(offset) {
  const now = new Date()
  return {
    start: new Date(now.getFullYear(), now.getMonth() + offset, 1),
    end: new Date(now.getFullYear(), now.getMonth() + offset + 1, 0),
  }
}

function formatDateInput(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

async function refreshRules() {
  rules.value = await listRules()
}

async function refreshRuns() {
  runHistory.value = await listRuns({ ...runFilters, limit: 200 })
}

async function openResults() {
  tab.value = 'result'
  await refreshRuns()
}

function forceUsd(config) {
  const next = JSON.parse(JSON.stringify(config || {}))
  next.extraParams = { ...(next.extraParams || {}), currencyCode: 'USD' }
  return next
}

function firstSource(rule, type) {
  return (rule.sources || []).find((source) => source.type === type)
}

function normalizeMapping(mapping) {
  return { ...defaultStoreMapping(), ...(mapping || {}) }
}

function normalizeRule(rule) {
  const warehouse = firstSource(rule, 'warehouse')
  const erp = firstSource(rule, 'erp')
  return {
    name: rule.name,
    warehouse_table: rule.warehouse_table || warehouse?.table_or_path || '',
    warehouse_date_field: rule.warehouse_date_field || warehouse?.date_field || 'dataDate',
    warehouse_store_field: rule.warehouse_store_field || warehouse?.store_field || 'storeName',
    warehouse_store_mapping: normalizeMapping(warehouse?.store_mapping),
    erp_module_path: rule.erp_module_path || erp?.table_or_path || '',
    erp_date_field: rule.erp_date_field || erp?.date_field || 'date',
    erp_store_field: rule.erp_store_field || erp?.store_field || 'storeName',
    erp_period_mode: erp?.period_mode || 'response_field',
    erp_store_mapping: normalizeMapping(erp?.store_mapping),
    erp_request_config: forceUsd(rule.erp_request_config || erp?.request_config || defaultRequestConfig()),
    metrics: rule.metrics?.length ? rule.metrics : (warehouse?.metrics || erp?.metrics || [emptyMetric()]),
  }
}

function resetRuleForm() {
  Object.assign(ruleForm, emptyRule())
  erpRequestConfigText.value = JSON.stringify(defaultRequestConfig(), null, 2)
  editingRuleId.value = null
}

function editRule(rule) {
  const normalized = normalizeRule(rule)
  Object.assign(ruleForm, normalized)
  erpRequestConfigText.value = JSON.stringify(normalized.erp_request_config, null, 2)
  editingRuleId.value = rule.id
}

function addMetric() {
  ruleForm.metrics.push(emptyMetric())
}

function removeMetric(index) {
  ruleForm.metrics.splice(index, 1)
}

function payloadFromForm() {
  const erpRequestConfig = forceUsd(JSON.parse(erpRequestConfigText.value || '{}'))
  const erpDateField = ruleForm.erp_period_mode === 'request_month' ? '' : ruleForm.erp_date_field
  return {
    name: ruleForm.name,
    warehouse_table: ruleForm.warehouse_table,
    warehouse_date_field: ruleForm.warehouse_date_field,
    warehouse_store_field: ruleForm.warehouse_store_field,
    erp_module_path: ruleForm.erp_module_path,
    erp_date_field: erpDateField,
    erp_store_field: ruleForm.erp_store_field,
    erp_request_config: erpRequestConfig,
    metrics: ruleForm.metrics,
    comparison_base_source: '数仓',
    sources: [
      {
        name: '数仓',
        type: 'warehouse',
        table_or_path: ruleForm.warehouse_table,
        date_field: ruleForm.warehouse_date_field,
        store_field: ruleForm.warehouse_store_field,
        period_mode: 'response_field',
        request_config: {},
        metrics: ruleForm.metrics,
        store_mapping: ruleForm.warehouse_store_mapping,
      },
      {
        name: 'ERP',
        type: 'erp',
        table_or_path: ruleForm.erp_module_path,
        date_field: erpDateField,
        store_field: ruleForm.erp_store_field,
        period_mode: ruleForm.erp_period_mode,
        request_config: erpRequestConfig,
        metrics: ruleForm.metrics,
        store_mapping: ruleForm.erp_store_mapping,
      },
    ],
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

async function runBatch() {
  running.value = true
  cancelling.value = false
  failedRuns.value = []
  currentJob.value = null
  clearJobPolling()
  try {
    const job = await startBatchRunJob({ ...runForm, rule_ids: selectedRuleIds.value })
    currentJob.value = job
    notify('任务已提交，正在后台运行。可以停留在本页查看进度。', 'info')
    jobPollTimer.value = window.setInterval(() => pollBatchJob(job.job_id), 2000)
    await pollBatchJob(job.job_id)
  } catch (error) {
    notify(`运行失败：${error.message}`, 'error')
    running.value = false
  } finally {
    // Completion is handled by pollBatchJob so long-running requests never block the UI thread.
  }
}

async function pollBatchJob(jobId) {
  try {
    const job = await getBatchRunJob(jobId)
    currentJob.value = job
    if (!['completed', 'cancelled'].includes(job.status)) return
    clearJobPolling()
    running.value = false
    cancelling.value = false
    if (job.status === 'cancelled') {
      notify('任务已取消', 'info')
      return
    }
    failedRuns.value = job.failed_runs || []
    notify(`运行完成：成功 ${job.runs.length} 个，失败 ${failedRuns.value.length} 个`, failedRuns.value.length ? 'error' : 'success')
    selectedRunIds.value = job.runs.map((run) => run.id)
    selectedRuns.value = job.runs
    await refreshRuns()
    if (!failedRuns.value.length) tab.value = 'result'
  } catch (error) {
    clearJobPolling()
    running.value = false
    cancelling.value = false
    notify(`进度刷新失败：${error.message}。可到结果查看页刷新历史记录。`, 'error')
  }
}

async function cancelCurrentJob() {
  if (!currentJob.value?.job_id) return
  if (!window.confirm('确认取消当前对账任务？已保存的历史结果不会删除。')) return
  cancelling.value = true
  try {
    currentJob.value = await cancelBatchRunJob(currentJob.value.job_id)
    notify('已发送取消请求，正在停止后续步骤。', 'info')
  } catch (error) {
    cancelling.value = false
    notify(`取消失败：${error.message}`, 'error')
  }
}

function clearJobPolling() {
  if (jobPollTimer.value) {
    window.clearInterval(jobPollTimer.value)
    jobPollTimer.value = null
  }
}

async function syncSelectedRuns() {
  const runIds = normalizeRunIds(selectedRunIds.value)
  selectedRunIds.value = runIds
  try {
    selectedRuns.value = await Promise.all(runIds.map((runId) => getRun(runId)))
  } catch (error) {
    selectedRuns.value = []
    notify(`加载运行结果失败：${error.message}。请刷新历史记录后重试。`, 'error')
  }
}

async function selectRun(run) {
  selectedRunIds.value = [Number(run.id)]
  selectedRuns.value = [await getRun(run.id)]
  tab.value = 'result'
  await refreshRuns()
}

async function removeRun(run) {
  if (!window.confirm(`确认删除运行记录 #${run.id}？规则不会被删除。`)) return
  try {
    await deleteRun(run.id)
    selectedRunIds.value = selectedRunIds.value.filter((id) => id !== run.id)
    selectedRuns.value = selectedRuns.value.filter((item) => item.id !== run.id)
    await refreshRuns()
    notify(`运行记录 #${run.id} 已删除`, 'success')
  } catch (error) {
    notify(`删除失败：${error.message}`, 'error')
  }
}

function normalizeRunIds(ids) {
  return Array.from(new Set(ids.map((id) => Number(id)).filter((id) => Number.isFinite(id))))
}

function filterLabel(values, allLabel, unit) {
  if (!values.length) return allLabel
  if (values.length === 1) return values[0]
  return `已选 ${values.length} 个${unit}`
}

function toggleFilterMenu(menu) {
  openFilterMenu.value = openFilterMenu.value === menu ? '' : menu
}

function closeFilterMenu() {
  openFilterMenu.value = ''
}

function clearFilter(key) {
  compareFilters[key] = []
  openFilterMenu.value = ''
}

function toggleFilterValue(key, value) {
  const values = compareFilters[key]
  compareFilters[key] = values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value]
}

function buildCompareRows(allowedRuleNames = null) {
  const groups = new Map()
  for (const run of selectedRuns.value) {
    if (allowedRuleNames && !allowedRuleNames.has(run.rule_name)) continue
    for (const row of run.summary_rows || []) {
      const period = formatPeriodMonth(row.period)
      const key = `${period}__${row.metric}`
      if (!groups.has(key)) groups.set(key, { key, period, metric: row.metric, warehouse: 0, erp: 0, diff: 0 })
      const group = groups.get(key)
      const values = sourceAmounts(row)
      group.warehouse += values.warehouse
      group.erp += values.erp
      group.diff += values.diff
    }
  }
  return Array.from(groups.values()).sort((a, b) => a.period.localeCompare(b.period) || a.metric.localeCompare(b.metric, 'zh-CN'))
}

function sourceAmounts(row) {
  const values = row.values || {}
  const warehouse = Number(values['数仓'] ?? values['鏁颁粨'] ?? values.warehouse ?? values.Warehouse ?? 0)
  const erp = Number(values.ERP ?? values.erp ?? 0)
  const diff = Number(row.diffs?.ERP ?? row.diffs?.erp ?? (warehouse - erp))
  return { warehouse, erp, diff }
}

function formatPeriodMonth(value) {
  return String(value || '').slice(0, 7)
}

function toggleExpand(key) {
  expandedKey.value = expandedKey.value === key ? '' : key
}

function detailRows(summary) {
  const groups = new Map()
  for (const run of selectedRuns.value) {
    for (const row of run.rows || []) {
      if (formatPeriodMonth(row.period) !== summary.period || row.metric !== summary.metric) continue
      if (!groups.has(row.store)) {
        groups.set(row.store, { store: row.store, warehouse: 0, erp: 0, fallbackWarehouse: 0, hasWarehouseSource: false })
      }
      const group = groups.get(row.store)
      if (isWarehouseSource(row.source)) {
        group.warehouse += Number(row.value ?? row.warehouse_value ?? 0)
        group.hasWarehouseSource = true
      } else if (isErpSource(row.source)) {
        group.erp += Number(row.value ?? row.erp_value ?? 0)
        group.fallbackWarehouse += Number(row.warehouse_value ?? 0)
      } else {
        group.warehouse += Number(row.warehouse_value ?? 0)
        group.erp += Number(row.erp_value ?? row.value ?? 0)
      }
    }
  }
  return Array.from(groups.values())
    .map((row) => {
      const warehouse = row.hasWarehouseSource ? row.warehouse : row.fallbackWarehouse
      return { store: row.store, warehouse, erp: row.erp, diff: warehouse - row.erp }
    })
    .sort((a, b) => {
      const diffOrder = Math.abs(b.diff) - Math.abs(a.diff)
      return diffOrder || String(a.store).localeCompare(String(b.store), 'zh-CN')
    })
}

function isWarehouseSource(source) {
  return ['数仓', '鏁颁粨', 'warehouse', 'Warehouse'].includes(source)
}

function isErpSource(source) {
  return ['ERP', 'erp'].includes(source)
}

async function downloadCompare() {
  try {
    await exportCompareRuns(selectedRunIds.value)
  } catch (error) {
    notify(`导出失败：${error.message}`, 'error')
  }
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN', { maximumFractionDigits: 4 })
}

function formatDateTime(value) {
  return String(value).replace('T', ' ').slice(0, 16)
}

onMounted(async () => {
  try {
    await refreshRules()
    await refreshRuns()
  } catch (error) {
    notify(error.message, 'error')
  }
})

onBeforeUnmount(() => {
  clearJobPolling()
})
</script>
