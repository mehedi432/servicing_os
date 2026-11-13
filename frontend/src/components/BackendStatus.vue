<script setup>
import { ref, onMounted } from 'vue'
import { getAppInfo } from '../api/frappe.js'

const info = ref(null)
const loading = ref(true)
const error = ref('')

async function loadAppInfo() {
  loading.value = true
  error.value = ''

  try {
    info.value = await getAppInfo()
  } catch (err) {
    error.value = err.message || 'Unable to connect'
  } finally {
    loading.value = false
  }
}

onMounted(loadAppInfo)
</script>

<template>
  <div class="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm">
    <span
      class="h-2.5 w-2.5 rounded-full"
      :class="loading ? 'bg-amber-400' : error ? 'bg-red-500' : 'bg-emerald-500'"
    ></span>

    <span v-if="loading" class="text-slate-500">
      Connecting to Frappe...
    </span>

    <template v-else-if="error">
      <span class="text-red-600">
        Backend connection failed: {{ error }}
      </span>
      <button
        class="rounded border px-2 py-1 text-xs"
        @click="loadAppInfo"
      >
        Retry
      </button>
    </template>

    <template v-else>
      <span class="font-semibold text-slate-800">
        {{ info.app_title }}
      </span>
      <span class="text-slate-500">
        User: {{ info.full_name }}
      </span>
      <span class="text-slate-500">
        Currency: {{ info.currency }}
      </span>
      <span class="font-medium text-emerald-700">
        Backend Connected
      </span>
    </template>
  </div>
</template>
