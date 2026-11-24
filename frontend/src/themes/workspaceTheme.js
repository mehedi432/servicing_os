import { computed, ref } from 'vue'

const storageKey = 'servicing-os-workspace-theme'
const colorRoles = ['canvas', 'surface', 'tint', 'border', 'ink', 'muted', 'accent', 'strong', 'selection']

export const workspaceThemes = [
  {
    id: 'ivory', label: 'Ivory', bangla: 'আইভরি',
    description: 'Warm cream and espresso', banglaDescription: 'উষ্ণ ক্রিম ও এসপ্রেসো',
    colors: ['#f8f6f0', '#fffefa', '#f3ebe0', '#e5d6c4', '#38291f', '#6d5b4c', '#785238', '#644229', '#e8d9c6'],
  },
  {
    id: 'paper-ink', label: 'Paper & Ink', bangla: 'পেপার অ্যান্ড ইংক',
    description: 'White paper, black ink, and soft grey', banglaDescription: 'সাদা কাগজ, কালো কালি ও হালকা ধূসর',
    colors: ['#f5f5f5', '#ffffff', '#eeeeee', '#d5d5d5', '#171717', '#525252', '#262626', '#111111', '#e1e1e1'],
  },
  {
    id: 'sandstone', label: 'Sandstone', bangla: 'স্যান্ডস্টোন',
    description: 'Soft sand and taupe', banglaDescription: 'হালকা বালুরঙ ও টোপ',
    colors: ['#f7f3ec', '#fffcf7', '#f1e6d6', '#dfcfb9', '#383028', '#615548', '#786144', '#5e4a31', '#e8dac6'],
  },
  {
    id: 'rose', label: 'Rose Mist', bangla: 'রোজ মিস্ট',
    description: 'Blush and muted rose', banglaDescription: 'হালকা গোলাপি ও মৃদু রোজ',
    colors: ['#faf3f5', '#fffafb', '#f5e5ec', '#e7cdd9', '#382b34', '#685361', '#8a4f6b', '#66374f', '#eed8e3'],
  },
  {
    id: 'lilac', label: 'Lilac Haze', bangla: 'লাইলাক হেজ',
    description: 'Lavender and soft plum', banglaDescription: 'ল্যাভেন্ডার ও হালকা প্লাম',
    colors: ['#f5f2f9', '#fcfaff', '#ede6f6', '#ded2eb', '#332a40', '#645671', '#6d518d', '#50376e', '#e4d9f1'],
  },
  {
    id: 'cloud', label: 'Cloud Blue', bangla: 'ক্লাউড ব্লু',
    description: 'Pale sky and dusty blue', banglaDescription: 'হালকা আকাশি ও মৃদু নীল',
    colors: ['#eff4fa', '#f9fcff', '#e4edf7', '#ccddeb', '#233244', '#4b6075', '#426993', '#2f506f', '#dae7f5'],
  },
  {
    id: 'sea-glass', label: 'Sea Glass', bangla: 'সি গ্লাস',
    description: 'Cool mint and soft teal', banglaDescription: 'শীতল মিন্ট ও হালকা টিল',
    colors: ['#eff6f4', '#f9fdfa', '#e3f0eb', '#c7e0d7', '#253832', '#4d645d', '#416f60', '#305549', '#d8ebe3'],
  },
  {
    id: 'apricot', label: 'Apricot Cream', bangla: 'এপ্রিকট ক্রিম',
    description: 'Light peach and muted terracotta', banglaDescription: 'হালকা পিচ ও মৃদু টেরাকোটা',
    colors: ['#fcf3ed', '#fffcf9', '#f7e4d7', '#ead0c0', '#392a25', '#68534a', '#874f3d', '#693726', '#f2dace'],
  },
  {
    id: 'sage-linen', label: 'Sage Linen', bangla: 'সেজ লিনেন',
    description: 'Pale sage and oatmeal', banglaDescription: 'হালকা সেজ ও ওটমিল',
    colors: ['#f4f5ed', '#fcfdf7', '#eaeddf', '#d9decc', '#303327', '#535f4b', '#59674e', '#404c36', '#e1e6d6'],
  },
  {
    id: 'buttercream', label: 'Buttercream', bangla: 'বাটারক্রিম',
    description: 'Soft yellow and muted ochre', banglaDescription: 'হালকা হলুদ ও মৃদু গেরুয়া',
    colors: ['#fbf7e9', '#fffdf5', '#f4ebd1', '#e5d7b0', '#393224', '#62543b', '#765a2e', '#594522', '#efe3c3'],
  },
]

const themesById = new Map(workspaceThemes.map(theme => [theme.id, theme]))
const defaultTheme = workspaceThemes[0]
function fromStorage(value) {
  return themesById.get(value) || defaultTheme
}
function readTheme() {
  try { return fromStorage(window.localStorage.getItem(storageKey)) }
  catch { return defaultTheme }
}
const saved = ref(readTheme())
const previewed = ref(null)
export const savedTheme = computed(() => saved.value)
export const visibleTheme = computed(() => previewed.value || saved.value)
export const hasThemePreview = computed(() => visibleTheme.value.id !== saved.value.id)

export function themeVariables(theme, prefix = '--os-') {
  return Object.fromEntries(colorRoles.map((role, index) => [prefix + role, theme.colors[index]]))
}

function renderTheme() {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  const theme = visibleTheme.value
  for (const [key, value] of Object.entries(themeVariables(theme))) root.style.setProperty(key, value)
  root.dataset.servicingTheme = theme.id
}

export function previewTheme(id) {
  const theme = themesById.get(id)
  if (!theme) return
  previewed.value = theme.id === saved.value.id ? null : theme
  renderTheme()
}

export function cancelThemePreview() {
  if (!previewed.value) return
  previewed.value = null
  renderTheme()
}

export function saveTheme() {
  if (!hasThemePreview.value) return true
  saved.value = visibleTheme.value
  previewed.value = null
  renderTheme()
  try {
    window.localStorage.setItem(storageKey, saved.value.id)
    return true
  } catch {
    return false
  }
}

if (typeof window !== 'undefined') {
  renderTheme()
  window.addEventListener('storage', event => {
    if (event.key !== storageKey) return
    saved.value = fromStorage(event.newValue)
    if (previewed.value?.id === saved.value.id) previewed.value = null
    renderTheme()
  })
}
