<template>
  <div>
    <div class="card">
      <h2>凭据查询</h2>
      <div class="row" style="margin-bottom: 12px">
        <div class="grow">
          <label>搜索关键词</label>
          <input
            v-model="q"
            type="text"
            placeholder="输入关键词…"
            style="width: 100%"
            @keydown.enter="doSearch()"
          />
        </div>
        <div>
          <label>字段</label>
          <select v-model="field">
            <option value="all">全部字段</option>
            <option value="domain">Domain</option>
            <option value="username">Username</option>
            <option value="password">Password</option>
          </select>
        </div>
        <div style="display: flex; align-items: center; gap: 6px; padding-bottom: 2px">
          <input type="checkbox" id="q-exact" v-model="exact" style="width: auto" />
          <label for="q-exact" style="margin: 0; cursor: pointer">精确匹配</label>
        </div>
        <button class="btn btn-primary" @click="doSearch()">搜索</button>
        <div style="display: flex; gap: 6px">
          <button class="btn btn-ghost" @click="exportData('csv')">导出 CSV</button>
          <button class="btn btn-ghost" @click="exportData('json')">导出 JSON</button>
        </div>
      </div>

      <div v-if="total !== null" style="font-size: .82rem; color: var(--muted); margin-bottom: 8px">
        共找到 {{ total.toLocaleString() }} 条记录
      </div>

      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>Domain</th>
              <th>URL</th>
              <th>Username</th>
              <th>Password</th>
              <th>首次录入</th>
              <th>来源</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="items.length === 0">
              <td colspan="6" style="text-align: center; color: var(--muted); padding: 24px">无结果</td>
            </tr>
            <tr v-for="r in items" :key="r.id">
              <td>
                {{ r.domain }}
                <button class="copy-btn" @click="copyText(r.domain)" title="复制">⎘</button>
              </td>
              <td style="max-width: 200px">{{ r.url }}</td>
              <td>
                {{ r.username }}
                <button class="copy-btn" @click="copyText(r.username)" title="复制">⎘</button>
              </td>
              <td>
                {{ r.password }}
                <button class="copy-btn" @click="copyText(r.password)" title="复制">⎘</button>
              </td>
              <td style="white-space: nowrap; color: var(--muted)">{{ fmtDate(r.first_seen) }}</td>
              <td style="color: var(--muted); font-size: .78rem">{{ r.source_file }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination">
        <button :disabled="page <= 1" @click="changePage(-1)">‹ 上一页</button>
        <span class="page-info">第 {{ page }} / {{ totalPages }} 页</span>
        <button :disabled="page >= totalPages" @click="changePage(1)">下一页 ›</button>
        <select v-model.number="pageSize" @change="doSearch()">
          <option :value="50">50 条/页</option>
          <option :value="100">100 条/页</option>
          <option :value="200">200 条/页</option>
        </select>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted } from 'vue'

const toast = inject('toast')

const q = ref('')
const field = ref('all')
const exact = ref(false)
const page = ref(1)
const pageSize = ref(50)
const total = ref(null)
const items = ref([])

const totalPages = computed(() => Math.ceil((total.value ?? 0) / pageSize.value) || 1)

async function doSearch(resetPage = true) {
  if (resetPage) page.value = 1
  try {
    const url = `/api/query?q=${encodeURIComponent(q.value)}&field=${field.value}&exact=${exact.value}&page=${page.value}&page_size=${pageSize.value}`
    const res = await fetch(url)
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    total.value = data.total
    items.value = data.items
  } catch (e) {
    toast('查询失败: ' + e.message, 'err')
  }
}

function changePage(delta) {
  page.value += delta
  doSearch(false)
}

function exportData(fmt) {
  const url = `/api/query/export?q=${encodeURIComponent(q.value)}&field=${field.value}&exact=${exact.value}&fmt=${fmt}`
  window.location.href = url
}

function copyText(text) {
  navigator.clipboard.writeText(text)
    .then(() => toast('已复制'))
    .catch(() => {
      const ta = document.createElement('textarea')
      ta.value = text
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      toast('已复制')
    })
}

function fmtDate(s) {
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}

onMounted(() => doSearch())
</script>

<style scoped>
.copy-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--muted);
  padding: 2px 4px;
  border-radius: 4px;
  font-size: .75rem;
  transition: .15s;
  margin-left: 4px;
}

.copy-btn:hover {
  color: var(--accent);
  background: var(--surface);
}

.pagination {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  justify-content: flex-end;
}

.pagination button {
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 5px 10px;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: .82rem;
}

.pagination button:disabled {
  opacity: .4;
  cursor: not-allowed;
}

.page-info {
  font-size: .82rem;
  color: var(--muted);
}
</style>
