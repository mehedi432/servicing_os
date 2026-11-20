<script setup>
import { nextTick, onMounted, onBeforeUnmount, ref, useId, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, required: true },
  placeholder: { type: String, default: 'Search by product name or item code' },
  lookup: { type: Function, required: true },
  emptyMessage: { type: String, default: 'No matching products.' },
  autofocus: Boolean,
  disabled: Boolean,
  selected: Boolean,
})
const emit = defineEmits(['update:modelValue', 'select'])
const id = useId()
const listId = `${id}-products`
const input = ref(null)
const visible = ref(false)
const loading = ref(false)
const products = ref([])
const active = ref(-1)
const message = ref('')
let timer, controller

function clearRequest() {
  clearTimeout(timer)
  controller?.abort()
  controller = null
}
function close() {
  clearRequest()
  visible.value = false
  active.value = -1
}
function search(text, delay = 0) {
  clearRequest()
  const query = text.trim()
  visible.value = true
  loading.value = true
  products.value = []
  active.value = -1
  message.value = ''
  controller = new AbortController()
  const signal = controller.signal
  timer = setTimeout(async () => {
    try {
      const matches = await props.lookup(query, signal)
      if (!signal.aborted) products.value = matches.slice(0, 8)
    } catch (error) {
      if (!signal.aborted) message.value = error.message || 'Product suggestions could not be loaded.'
    } finally {
      if (!signal.aborted) loading.value = false
    }
  }, delay)
}
function open() {
  if (!visible.value && !props.disabled) search(props.selected ? '' : props.modelValue)
}
function change(event) {
  const value = event.target.value
  emit('update:modelValue', value)
  search(value, 175)
}
function select(product) {
  if (props.disabled) return
  close()
  emit('select', product)
}
function keyboard(event) {
  if (event.key === 'Escape' && visible.value) {
    event.preventDefault()
    event.stopPropagation()
    close()
  } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    if (!visible.value) {
      open()
      return
    }
    const last = products.value.length - 1
    if (last < 0) return
    active.value = event.key === 'ArrowDown'
      ? (active.value + 1) % (last + 1)
      : (active.value <= 0 ? last : active.value - 1)
    nextTick(() => document.getElementById(`${listId}-${active.value}`)?.scrollIntoView?.({block:'nearest'}))
  } else if (event.key === 'Enter' && visible.value) {
    event.preventDefault()
    if (active.value >= 0) select(products.value[active.value])
  }
}

watch(() => props.disabled, disabled => { if (disabled) close() })
onMounted(() => { if (props.autofocus) input.value?.focus() })
onBeforeUnmount(clearRequest)
</script>

<template>
  <div class="sos-product-picker">
    <label class="sos-product-label" :for="id">
      <span>{{ label }}</span>
      <input ref="input" :id="id" :value="modelValue" :placeholder="placeholder" :disabled="disabled"
        type="search" autocomplete="off" role="combobox" aria-autocomplete="list"
        :aria-expanded="visible" :aria-controls="visible ? listId : undefined"
        :aria-activedescendant="visible && active >= 0 ? `${listId}-${active}` : undefined"
        @focus="open" @click="open" @input="change" @blur="close" @keydown="keyboard" />
    </label>
    <div v-if="visible" class="sos-product-panel">
      <p v-if="loading" role="status">Loading products…</p>
      <p v-else-if="message" role="alert">{{ message }}</p>
      <p v-else-if="!products.length" role="status">{{ emptyMessage }}</p>
      <div :id="listId" class="sos-product-grid" role="listbox" aria-label="Product suggestions" :aria-busy="loading">
        <button v-for="(product, index) in products" :id="`${listId}-${index}`" :key="product.code"
          type="button" role="option" tabindex="-1" :aria-selected="active === index"
          @pointerdown.prevent @mousedown.prevent @click="select(product)">
          <strong>{{ product.name || product.code }}</strong>
          <small>{{ product.code }}</small>
          <small v-if="product.detail">{{ product.detail }}</small>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sos-product-picker{display:grid;min-width:0;gap:7px}
.sos-product-panel{container: product-suggestions / inline-size;min-width:0;padding:7px;border:1px solid #e5cdb9;border-radius:10px;background:#f7ede2}
.sos-product-panel p{margin:0;padding:5px;color:#6e513d;font-size:12px}
.sos-product-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}
.sos-product-grid button{appearance:none;display:grid;align-content:start;gap:3px;min-width:0;padding:8px;text-align:left;overflow-wrap:anywhere;border:1px solid #e6d4c4;border-radius:8px;background:#fffdf9;color:#4c3628;font:inherit;cursor:pointer}
.sos-product-grid button:hover,.sos-product-grid button[aria-selected="true"]{border-color:#a86d4b;background:#f1e0cf}
.sos-product-grid strong{font-size:11px;font-weight:750}
.sos-product-grid small{color:#795f48;font-size:10px}
@container product-suggestions (max-width:540px){.sos-product-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
