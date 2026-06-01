<template>
  <div id="app-root">
    <nav>
      <span class="logo">🔍 PasswordInspector</span>
      <button :class="{ active: panel === 'query' }" @click="panel = 'query'">查询</button>
      <button :class="{ active: panel === 'upload' }" @click="panel = 'upload'">导入</button>
    </nav>
    <div id="content">
      <QueryPanel v-if="panel === 'query'" />
      <UploadPanel v-else-if="panel === 'upload'" />
    </div>
    <Teleport to="body">
      <div id="toast" :class="['toast', toastType, { show: toastVisible }]">{{ toastMsg }}</div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, provide } from 'vue'
import QueryPanel from './components/QueryPanel.vue'
import UploadPanel from './components/UploadPanel.vue'

const panel = ref('query')

// Global toast
const toastMsg = ref('')
const toastType = ref('ok')
const toastVisible = ref(false)
let toastTimer = null

function showToast(msg, type = 'ok') {
  toastMsg.value = msg
  toastType.value = type
  toastVisible.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastVisible.value = false }, 2800)
}

provide('toast', showToast)
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #0f1117;
  --surface: #1a1d27;
  --surface2: #22263a;
  --border: #2e3250;
  --accent: #4f8ef7;
  --accent2: #7c5cfc;
  --danger: #e05252;
  --success: #3ecf8e;
  --warn: #f0a030;
  --text: #e2e8f0;
  --muted: #8892a4;
  --radius: 8px;
  --font: 'Segoe UI', system-ui, sans-serif;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
  min-height: 100vh;
}

#app-root {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

nav {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 24px;
  height: 52px;
  flex-shrink: 0;
}

nav .logo {
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--accent);
  letter-spacing: .5px;
}

nav button {
  background: none;
  border: none;
  color: var(--muted);
  cursor: pointer;
  font-size: .9rem;
  padding: 6px 10px;
  border-radius: var(--radius);
  transition: .15s;
}

nav button:hover,
nav button.active {
  background: var(--surface2);
  color: var(--text);
}

#content {
  flex: 1;
  overflow: auto;
  padding: 24px;
}

/* card */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 16px;
}

.card h2 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 14px;
  color: var(--text);
}

/* form controls */
input, select {
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 8px 12px;
  border-radius: var(--radius);
  font-size: .9rem;
  outline: none;
  transition: .15s;
}

input:focus, select:focus {
  border-color: var(--accent);
}

label {
  font-size: .82rem;
  color: var(--muted);
  display: block;
  margin-bottom: 4px;
}

.row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.grow { flex: 1; min-width: 160px; }

/* buttons */
.btn {
  padding: 8px 16px;
  border-radius: var(--radius);
  border: none;
  cursor: pointer;
  font-size: .88rem;
  font-weight: 500;
  transition: .15s;
}

.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover { filter: brightness(1.15); }
.btn-danger { background: var(--danger); color: #fff; }
.btn-danger:hover { filter: brightness(1.15); }
.btn-ghost { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }
.btn-ghost:hover { border-color: var(--accent); color: var(--accent); }
.btn:disabled { opacity: .45; cursor: not-allowed; }

/* table */
.tbl-wrap { overflow-x: auto; }

table {
  width: 100%;
  border-collapse: collapse;
  font-size: .85rem;
}

th {
  background: var(--surface2);
  color: var(--muted);
  font-weight: 600;
  padding: 8px 12px;
  text-align: left;
  position: sticky;
  top: 0;
  border-bottom: 1px solid var(--border);
}

td {
  padding: 7px 12px;
  border-bottom: 1px solid var(--border);
  word-break: break-all;
  max-width: 320px;
}

tr:hover td { background: var(--surface2); }

/* badge */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: .75rem;
  font-weight: 600;
}

.badge-ok { background: #1a3a2a; color: var(--success); }
.badge-err { background: #3a1a1a; color: var(--danger); }
.badge-pending { background: #2a2a1a; color: var(--warn); }
.badge-processing { background: #1a2540; color: var(--accent); }

/* toast */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 18px;
  font-size: .88rem;
  box-shadow: 0 4px 20px #0006;
  opacity: 0;
  pointer-events: none;
  transition: .3s;
  z-index: 9999;
}

.toast.show { opacity: 1; }
.toast.ok { border-color: var(--success); color: var(--success); }
.toast.err { border-color: var(--danger); color: var(--danger); }

@media (max-width: 600px) {
  #content { padding: 12px; }
  .row { flex-direction: column; }
}
</style>
