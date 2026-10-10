<template>
  <div class="knowledge-page">
    <PageHeader title="政策知识库" description="上传、索引、验证并发布员工政策文档">
      <el-button :icon="Search" @click="openSearch()">检索测试</el-button>
      <el-button type="primary" :icon="UploadFilled" @click="openCreate">上传政策</el-button>
    </PageHeader>

    <section class="panel">
      <div class="knowledge-filters">
        <el-input
          v-model="filters.keyword"
          clearable
          placeholder="按政策名称搜索"
          :prefix-icon="Search"
          @keyup.enter="load"
        />
        <el-input v-model="filters.category" clearable placeholder="政策分类" @keyup.enter="load" />
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" row-key="id">
        <el-table-column prop="name" label="政策名称" min-width="220" />
        <el-table-column prop="category" label="分类" width="140">
          <template #default="{ row }">{{ row.category || '-' }}</template>
        </el-table-column>
        <el-table-column prop="current_version" label="当前发布版本" width="140">
          <template #default="{ row }">{{ row.current_version || '未发布' }}</template>
        </el-table-column>
        <el-table-column label="最新状态" width="130">
          <template #default="{ row }">
            <el-tag :type="statusMeta(row.latest_status).type" effect="plain">
              {{ statusMeta(row.latest_status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version_count" label="版本数" width="90" />
        <el-table-column label="更新时间" width="190">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">版本管理</el-button>
            <el-button link @click="openNewVersion(row)">上传新版本</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !rows.length" description="暂无政策文档" />
      <el-pagination
        v-if="total > filters.page_size"
        v-model:current-page="filters.page"
        v-model:page-size="filters.page_size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load"
      />
    </section>

    <el-dialog v-model="uploadVisible" :title="uploadMode === 'create' ? '上传政策' : '上传新版本'" width="620">
      <el-form label-position="top" class="knowledge-form">
        <el-form-item v-if="uploadMode === 'create'" label="政策名称" required>
          <el-input v-model="uploadForm.name" maxlength="200" placeholder="例如：员工休假管理办法" />
        </el-form-item>
        <el-form-item v-if="uploadMode === 'create'" label="政策分类">
          <el-input v-model="uploadForm.category" maxlength="100" placeholder="例如：考勤与休假" />
        </el-form-item>
        <el-form-item v-if="uploadMode === 'create'" label="说明">
          <el-input v-model="uploadForm.description" type="textarea" :rows="2" maxlength="2000" />
        </el-form-item>
        <el-form-item label="版本号" required>
          <el-input v-model="uploadForm.version" maxlength="50" placeholder="例如：1.0 或 2026-01" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="生效日期">
            <el-date-picker v-model="uploadForm.effective_from" value-format="YYYY-MM-DD" clearable />
          </el-form-item>
          <el-form-item label="失效日期">
            <el-date-picker v-model="uploadForm.effective_to" value-format="YYYY-MM-DD" clearable />
          </el-form-item>
        </div>
        <el-form-item label="政策文件" required>
          <el-upload
            class="knowledge-upload"
            drag
            :auto-upload="false"
            :limit="1"
            accept=".pdf,.docx,.md,.txt"
            :file-list="fileList"
            :on-change="fileChanged"
            :on-remove="fileRemoved"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖放文件到此处，或<em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">支持带文本层的 PDF、DOCX、MD、TXT，最大 20 MB；暂不支持扫描 PDF OCR。</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">上传并建立索引</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" size="72%" title="政策版本管理" @closed="stopPolling">
      <template v-if="detail">
        <div class="knowledge-summary">
          <div><span>政策名称</span><strong>{{ detail.name }}</strong></div>
          <div><span>分类</span><strong>{{ detail.category || '-' }}</strong></div>
          <div><span>版本数量</span><strong>{{ detail.versions.length }}</strong></div>
        </div>
        <el-alert
          v-if="hasProcessing"
          title="文档正在解析或向量化，页面会自动刷新状态。"
          type="info"
          :closable="false"
          show-icon
          class="knowledge-alert"
        />
        <el-table :data="detail.versions" row-key="id">
          <el-table-column prop="version" label="版本" width="110" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="statusMeta(row.status).type">{{ statusMeta(row.status).label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="original_filename" label="原文件" min-width="190" show-overflow-tooltip />
          <el-table-column prop="chunk_count" label="分块" width="80" />
          <el-table-column label="生效区间" min-width="190">
            <template #default="{ row }">{{ row.effective_from || '不限' }} 至 {{ row.effective_to || '不限' }}</template>
          </el-table-column>
          <el-table-column label="创建时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'READY'" link type="success" @click="publishVersion(row)">发布</el-button>
              <el-button v-if="row.status === 'FAILED'" link type="primary" @click="retryVersion(row)">重试</el-button>
              <el-button v-if="['READY', 'PUBLISHED'].includes(row.status)" link @click="openSearch(row.id)">检索测试</el-button>
              <el-button v-if="['READY', 'PUBLISHED'].includes(row.status)" link type="danger" @click="archiveVersion(row)">归档</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-alert
          v-for="version in failedVersions"
          :key="version.id"
          :title="`版本 ${version.version}：${version.failure_reason || '索引失败'}`"
          type="error"
          show-icon
          :closable="false"
          class="knowledge-alert"
        />
      </template>
    </el-drawer>

    <el-dialog v-model="searchVisible" title="政策检索测试" width="760">
      <el-alert
        title="此功能用于发布前验证向量召回片段，不会调用大模型生成回答。"
        type="info"
        :closable="false"
        class="knowledge-alert"
      />
      <div class="search-bar">
        <el-input v-model="searchForm.query" placeholder="输入员工可能提出的政策问题" @keyup.enter="runSearch" />
        <el-button type="primary" :loading="searching" :icon="Search" @click="runSearch">检索</el-button>
      </div>
      <div v-if="searchResults.length" class="search-results">
        <article v-for="item in searchResults" :key="item.chunk_id" class="search-result">
          <div class="search-result-meta">
            <span>相似度 {{ Math.round(item.score * 100) }}%</span>
            <span>{{ item.section || '未标记章节' }}</span>
            <span v-if="item.page_number">第 {{ item.page_number }} 页</span>
          </div>
          <p>{{ item.content }}</p>
        </article>
      </div>
      <el-empty v-else-if="searched && !searching" description="未召回相关片段" />
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, UploadFilled } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import { knowledgeApi } from '../api'
import { formatDateTime } from '../utils/datetime'

const processingStatuses = ['UPLOADED', 'PARSING', 'INDEXING']
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const uploadVisible = ref(false)
const uploading = ref(false)
const uploadMode = ref('create')
const selectedDocument = ref(null)
const selectedFile = ref(null)
const fileList = ref([])
const detailVisible = ref(false)
const detail = ref(null)
const searchVisible = ref(false)
const searching = ref(false)
const searched = ref(false)
const searchResults = ref([])
let pollingTimer = null

const filters = reactive({ keyword: '', category: '', page: 1, page_size: 20 })
const uploadForm = reactive({
  name: '',
  category: '',
  description: '',
  version: '',
  effective_from: '',
  effective_to: '',
})
const searchForm = reactive({ query: '', version_id: null })
const hasProcessing = computed(() => detail.value?.versions.some((item) => processingStatuses.includes(item.status)))
const failedVersions = computed(() => detail.value?.versions.filter((item) => item.status === 'FAILED') || [])

const statusMap = {
  UPLOADED: { label: '待处理', type: 'info' },
  PARSING: { label: '解析中', type: 'primary' },
  INDEXING: { label: '向量化中', type: 'primary' },
  READY: { label: '待发布', type: 'warning' },
  PUBLISHED: { label: '已发布', type: 'success' },
  ARCHIVED: { label: '已归档', type: 'info' },
  FAILED: { label: '失败', type: 'danger' },
}
function statusMeta(status) {
  return statusMap[status] || { label: status || '-', type: 'info' }
}

async function load() {
  loading.value = true
  try {
    const response = await knowledgeApi.list(filters)
    rows.value = response.data?.items || []
    total.value = response.data?.total || 0
  } catch (error) {
    ElMessage.error(error.businessMessage)
  } finally {
    loading.value = false
  }
}
function resetFilters() {
  Object.assign(filters, { keyword: '', category: '', page: 1 })
  load()
}
function resetUpload() {
  Object.assign(uploadForm, { name: '', category: '', description: '', version: '', effective_from: '', effective_to: '' })
  selectedFile.value = null
  fileList.value = []
}
function openCreate() {
  uploadMode.value = 'create'
  selectedDocument.value = null
  resetUpload()
  uploadVisible.value = true
}
function openNewVersion(row) {
  uploadMode.value = 'version'
  selectedDocument.value = row
  resetUpload()
  uploadVisible.value = true
}
function fileChanged(file) {
  selectedFile.value = file.raw
  fileList.value = [file]
}
function fileRemoved() {
  selectedFile.value = null
  fileList.value = []
}
async function submitUpload() {
  if (uploadMode.value === 'create' && !uploadForm.name.trim()) return ElMessage.warning('请输入政策名称')
  if (!uploadForm.version.trim()) return ElMessage.warning('请输入版本号')
  if (!selectedFile.value) return ElMessage.warning('请选择政策文件')
  if (uploadForm.effective_from && uploadForm.effective_to && uploadForm.effective_to < uploadForm.effective_from)
    return ElMessage.warning('失效日期不能早于生效日期')
  const data = new FormData()
  for (const [key, value] of Object.entries(uploadForm)) if (value) data.append(key, value)
  data.append('file', selectedFile.value)
  uploading.value = true
  try {
    if (uploadMode.value === 'create') await knowledgeApi.create(data)
    else await knowledgeApi.uploadVersion(selectedDocument.value.id, data)
    ElMessage.success('文件已上传，正在建立索引')
    uploadVisible.value = false
    await load()
    if (selectedDocument.value) await openDetail(selectedDocument.value)
  } catch (error) {
    ElMessage.error(error.businessMessage)
  } finally {
    uploading.value = false
  }
}
async function refreshDetail() {
  if (!detail.value?.id) return
  try {
    detail.value = (await knowledgeApi.detail(detail.value.id)).data
    if (!hasProcessing.value) stopPolling()
  } catch (error) {
    stopPolling()
    ElMessage.error(error.businessMessage)
  }
}
async function openDetail(row) {
  stopPolling()
  try {
    detail.value = (await knowledgeApi.detail(row.id)).data
    detailVisible.value = true
    if (hasProcessing.value) pollingTimer = window.setInterval(refreshDetail, 3000)
  } catch (error) {
    ElMessage.error(error.businessMessage)
  }
}
function stopPolling() {
  if (pollingTimer) window.clearInterval(pollingTimer)
  pollingTimer = null
}
async function publishVersion(row) {
  try {
    await ElMessageBox.confirm(`确认发布版本 ${row.version}？当前已发布版本将自动归档。`, '发布政策', { type: 'warning' })
    await knowledgeApi.publish(row.id)
    ElMessage.success('政策版本已发布')
    await Promise.all([refreshDetail(), load()])
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error.businessMessage)
  }
}
async function retryVersion(row) {
  try {
    await knowledgeApi.retry(row.id)
    ElMessage.success('已重新提交索引任务')
    await refreshDetail()
    if (!pollingTimer) pollingTimer = window.setInterval(refreshDetail, 3000)
  } catch (error) {
    ElMessage.error(error.businessMessage)
  }
}
async function archiveVersion(row) {
  try {
    await ElMessageBox.confirm(`确认归档版本 ${row.version}？归档后不会参与员工政策问答。`, '归档政策', { type: 'warning' })
    await knowledgeApi.archive(row.id)
    ElMessage.success('政策版本已归档')
    await Promise.all([refreshDetail(), load()])
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error.businessMessage)
  }
}
function openSearch(versionId = null) {
  searchForm.version_id = versionId
  searchForm.query = ''
  searchResults.value = []
  searched.value = false
  searchVisible.value = true
}
async function runSearch() {
  if (!searchForm.query.trim()) return ElMessage.warning('请输入检索问题')
  searching.value = true
  searched.value = false
  try {
    searchResults.value = (await knowledgeApi.search({ ...searchForm, query: searchForm.query.trim() })).data || []
    searched.value = true
  } catch (error) {
    ElMessage.error(error.businessMessage)
  } finally {
    searching.value = false
  }
}

onMounted(load)
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.knowledge-filters{display:grid;grid-template-columns:minmax(240px,1fr) 180px auto auto;gap:12px;margin-bottom:18px}.knowledge-form{padding:0 4px}.knowledge-upload{width:100%}.knowledge-upload :deep(.el-upload),.knowledge-upload :deep(.el-upload-dragger){width:100%}.knowledge-summary{display:grid;grid-template-columns:2fr 1fr 1fr;gap:1px;background:#e9edf2;border:1px solid #e9edf2;margin-bottom:18px}.knowledge-summary>div{background:#fff;padding:16px;display:flex;flex-direction:column;gap:6px}.knowledge-summary span{font-size:12px;color:#7c8997}.knowledge-summary strong{font-size:15px}.knowledge-alert{margin:14px 0}.search-bar{display:grid;grid-template-columns:1fr auto;gap:10px;margin:16px 0}.search-results{display:flex;flex-direction:column;gap:10px;max-height:480px;overflow:auto}.search-result{border:1px solid #e5eaf0;border-radius:6px;padding:14px}.search-result-meta{display:flex;gap:14px;color:#64748b;font-size:12px}.search-result p{white-space:pre-wrap;line-height:1.7;margin:10px 0 0;font-size:13px;color:#334155}@media(max-width:800px){.knowledge-filters{grid-template-columns:1fr}.knowledge-summary{grid-template-columns:1fr}.search-bar{grid-template-columns:1fr}}
</style>
