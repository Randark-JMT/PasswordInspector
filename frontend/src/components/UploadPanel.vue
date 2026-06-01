<template>
  <div>
    <!-- File picker -->
    <div class="card">
      <h2>导入数据文件</h2>
      <div
        class="dropzone"
        :class="{ dragover: isDragover }"
        @click="fileInput?.click()"
        @dragover.prevent="isDragover = true"
        @dragleave="isDragover = false"
        @drop.prevent="onDrop"
      >
        <input
          ref="fileInput"
          type="file"
          style="display: none"
          @change="onFileChange"
        />
        <div style="font-size: 2rem; margin-bottom: 8px">📂</div>
        <div>点击选择文件，或拖拽到此处</div>
        <div style="font-size: .8rem; margin-top: 6px">支持任意文本格式，文件大小不限</div>
      </div>
    </div>

    <!-- Job progress -->
    <template v-if="phase !== 'idle'">
      <div class="card">
        <h2>导入进度</h2>
        <div style="color: var(--muted); font-size: .85rem; margin-bottom: 8px">
          {{ filename }} &nbsp; {{ fmtBytes(localFileSize) }}
        </div>

        <!-- Phase label -->
        <div style="font-size: .78rem; color: var(--muted); margin-bottom: 4px">
          <span v-if="phase === 'uploading'">📤 上传中…</span>
          <span v-else-if="phase === 'processing'">⚙️ 解析处理中…</span>
          <span v-else-if="phase === 'done'">✅ 完成</span>
          <span v-else-if="phase === 'error'" style="color: var(--danger)">❌ 出错</span>
        </div>

        <div class="progress-wrap">
          <div class="progress-bar" :style="{ width: displayPct + '%' }"></div>
        </div>

        <div class="stat-row">
          <span>状态:
            <b><span class="badge" :class="badgeClass">{{ jobStatus || phase }}</span></b>
          </span>
          <template v-if="phase !== 'uploading'">
            <span>已处理: <b>{{ fmtBytes(processedBytes) }}</b></span>
            <span>总行数: <b>{{ totalLines.toLocaleString() }}</b></span>
            <span>已导入: <b>{{ importedLines.toLocaleString() }}</b></span>
            <span>解析失败: <b>{{ failedLinesCount.toLocaleString() }}</b></span>
          </template>
          <template v-else>
            <span>已上传: <b>{{ fmtBytes(uploadedBytes) }} / {{ fmtBytes(localFileSize) }}</b></span>
          </template>
        </div>
        <div v-if="errorMessage" style="color: var(--danger); font-size: .82rem; margin-top: 8px">
          {{ errorMessage }}
        </div>
      </div>

      <!-- Failed lines -->
      <div v-if="failedLines.length" class="card">
        <h2>⚠️ 无法解析的条目 — 请手动处理</h2>
        <div
          v-for="line in failedLines"
          :key="line.id"
          class="fail-item"
        >
          <div class="fail-raw">{{ line.raw }}</div>
          <div class="fail-fields">
            <div><label>URL</label><input v-model="line._url" placeholder="https://example.com" /></div>
            <div><label>Username</label><input v-model="line._username" placeholder="用户名" /></div>
            <div><label>Password</label><input v-model="line._password" placeholder="密码" /></div>
            <button class="btn btn-primary" @click="resolveLine(line)">保存</button>
            <button class="btn btn-danger" @click="discardLine(line)">忽略</button>
          </div>
        </div>
        <div style="margin-top: 12px">
          <button class="btn btn-ghost" @click="discardAll">全部忽略</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, inject } from 'vue'

const toast = inject('toast')

const fileInput = ref(null)
const isDragover = ref(false)

// phase: 'idle' | 'uploading' | 'processing' | 'done' | 'error'
const phase = ref('idle')
const jobId = ref(null)
const filename = ref('')
const localFileSize = ref(0)   // browser-side File.size for upload phase progress
const uploadedBytes = ref(0)   // XHR upload progress

const jobStatus = ref('')
const processedBytes = ref(0)
const totalLines = ref(0)
const importedLines = ref(0)
const failedLinesCount = ref(0)
const errorMessage = ref('')
const failedLines = ref([])

let pollTimer = null

// Progress percentage:
// - uploading phase: uploadedBytes / localFileSize
// - processing phase: processedBytes / job.total_bytes (from server)
const serverTotalBytes = ref(0)
const displayPct = computed(() => {
  if (phase.value === 'uploading') {
    if (!localFileSize.value) return 0
    return Math.min(100, (uploadedBytes.value / localFileSize.value) * 100).toFixed(1)
  }
  if (!serverTotalBytes.value) return 0
  return Math.min(100, (processedBytes.value / serverTotalBytes.value) * 100).toFixed(1)
})

const badgeClass = computed(() => ({
  'badge-ok': phase.value === 'done',
  'badge-err': phase.value === 'error',
  'badge-processing': phase.value === 'processing',
  'badge-pending': phase.value === 'uploading',
}))

function fmtBytes(b) {
  if (b < 1024) return b + ' B'
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB'
  if (b < 1073741824) return (b / 1048576).toFixed(1) + ' MB'
  return (b / 1073741824).toFixed(2) + ' GB'
}

function onFileChange(e) {
  const f = e.target.files?.[0]
  if (f) startUpload(f)
}

function onDrop(e) {
  isDragover.value = false
  const f = e.dataTransfer.files?.[0]
  if (f) startUpload(f)
}

function startUpload(file) {
  clearInterval(pollTimer)
  jobId.value = null
  failedLines.value = []
  filename.value = file.name
  localFileSize.value = file.size
  uploadedBytes.value = 0
  processedBytes.value = 0
  serverTotalBytes.value = 0
  totalLines.value = 0
  importedLines.value = 0
  failedLinesCount.value = 0
  errorMessage.value = ''
  jobStatus.value = ''
  phase.value = 'uploading'

  const fd = new FormData()
  fd.append('file', file)

  const xhr = new XMLHttpRequest()

  // Upload progress (browser → server)
  xhr.upload.addEventListener('progress', (e) => {
    if (e.lengthComputable) uploadedBytes.value = e.loaded
  })

  xhr.addEventListener('load', () => {
    if (xhr.status >= 200 && xhr.status < 300) {
      try {
        const job = JSON.parse(xhr.responseText)
        jobId.value = job.id
        serverTotalBytes.value = job.total_bytes
        phase.value = 'processing'
        jobStatus.value = job.status
        pollTimer = setInterval(pollJob, 1000)
      } catch {
        phase.value = 'error'
        errorMessage.value = '响应解析失败'
        toast('上传失败', 'err')
      }
    } else {
      phase.value = 'error'
      errorMessage.value = xhr.responseText
      toast('上传失败: ' + xhr.status, 'err')
    }
  })

  xhr.addEventListener('error', () => {
    phase.value = 'error'
    errorMessage.value = '网络错误'
    toast('上传失败：网络错误', 'err')
  })

  xhr.open('POST', '/api/upload/start')
  xhr.send(fd)
}

async function pollJob() {
  try {
    const res = await fetch(`/api/upload/job/${jobId.value}`)
    const job = await res.json()
    processedBytes.value = job.processed_bytes
    serverTotalBytes.value = job.total_bytes
    totalLines.value = job.total_lines
    importedLines.value = job.imported_lines
    failedLinesCount.value = job.failed_lines
    jobStatus.value = job.status
    errorMessage.value = job.error_message

    if (job.status === 'done' || job.status === 'error') {
      clearInterval(pollTimer)
      phase.value = job.status
      if (job.failed_lines > 0) await loadFailedLines()
      toast(
        job.status === 'done'
          ? `导入完成，共 ${job.imported_lines.toLocaleString()} 条`
          : '导入出错',
        job.status === 'done' ? 'ok' : 'err',
      )
    }
  } catch (_) {}
}

async function loadFailedLines() {
  const res = await fetch(`/api/upload/job/${jobId.value}/failed`)
  const lines = await res.json()
  failedLines.value = lines.map(l => ({ ...l, _url: '', _username: '', _password: '' }))
}

async function resolveLine(line) {
  if (!line._username.trim()) { toast('Username 不能为空', 'err'); return }
  const res = await fetch(`/api/upload/job/${jobId.value}/failed/${line.id}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: line._url, username: line._username, password: line._password }),
  })
  if (res.ok) {
    failedLines.value = failedLines.value.filter(l => l.id !== line.id)
    toast('已保存')
  } else {
    toast('保存失败', 'err')
  }
}

async function discardLine(line) {
  const res = await fetch(`/api/upload/job/${jobId.value}/failed/${line.id}`, { method: 'DELETE' })
  if (res.ok) {
    failedLines.value = failedLines.value.filter(l => l.id !== line.id)
    toast('已忽略')
  }
}

async function discardAll() {
  await Promise.all(
    failedLines.value.map(l =>
      fetch(`/api/upload/job/${jobId.value}/failed/${l.id}`, { method: 'DELETE' })
    )
  )
  failedLines.value = []
  toast('已全部忽略')
}
</script>

<style scoped>
.dropzone {
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: .2s;
  color: var(--muted);
}

.dropzone:hover,
.dropzone.dragover {
  border-color: var(--accent);
  color: var(--accent);
}

.progress-wrap {
  background: var(--surface2);
  border-radius: 20px;
  height: 10px;
  overflow: hidden;
  margin: 10px 0;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  transition: width .3s;
}

.stat-row {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  font-size: .82rem;
  color: var(--muted);
  margin-top: 8px;
}

.stat-row b { color: var(--text); }

.fail-item {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px;
  margin-bottom: 10px;
}

.fail-raw {
  font-family: monospace;
  font-size: .82rem;
  color: var(--warn);
  word-break: break-all;
  margin-bottom: 10px;
}

.fail-fields {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.fail-fields input {
  flex: 1;
  min-width: 100px;
}
</style>
