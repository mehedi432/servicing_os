<script setup>
import { onBeforeUnmount, ref, useId } from 'vue'
import { currentLanguage } from '../i18n/servicingLanguage.js'
import {
  workspaceThemes, savedTheme, visibleTheme, hasThemePreview, themeVariables,
  previewTheme, cancelThemePreview, saveTheme,
} from '../themes/workspaceTheme.js'

const appearance = useId()
const savedMessage = ref('')
const tr = (english, bangla) => currentLanguage.value === 'bn' ? bangla : english
const label = theme => tr(theme.label, theme.bangla)
const description = theme => tr(theme.description, theme.banglaDescription)

function choose(id) {
  savedMessage.value = ''
  previewTheme(id)
}
function applyTheme() {
  const persisted = saveTheme()
  savedMessage.value = persisted
    ? tr('Theme saved.', 'থিম সংরক্ষিত হয়েছে।')
    : tr('Theme applied for this tab. Browser storage is unavailable.', 'এই ট্যাবে থিম প্রয়োগ করা হয়েছে। ব্রাউজার স্টোরেজ ব্যবহার করা যাচ্ছে না।')
}
onBeforeUnmount(cancelThemePreview)
</script>

<template>
  <section class="theme-settings" :aria-labelledby="appearance">
    <div class="theme-settings-header">
      <div>
        <h2 :id="appearance">{{ tr('Appearance', 'চেহারা') }}</h2>
        <p>{{ tr('Select a palette to preview it. Apply to keep it in this browser.', 'দেখতে একটি রঙের প্যালেট বেছে নিন। এই ব্রাউজারে রাখতে প্রয়োগ করুন।') }}</p>
      </div>
      <span class="theme-current">
        {{ hasThemePreview ? tr('Preview', 'প্রিভিউ') : tr('Active theme', 'সক্রিয় থিম') }} · {{ label(visibleTheme) }}
      </span>
    </div>

    <fieldset class="theme-options">
      <legend class="sr-only">{{ tr('Workspace colour theme', 'ওয়ার্কস্পেসের রঙের থিম') }}</legend>
      <label v-for="theme in workspaceThemes" :key="theme.id" class="theme-option">
        <input type="radio" class="sr-only" :name="appearance + '-theme'" :value="theme.id"
          :checked="visibleTheme.id === theme.id" @change="choose(theme.id)">
        <span class="theme-option-body">
          <span class="theme-sample" :style="themeVariables(theme, '--sample-')" aria-hidden="true">
            <span class="theme-sample-nav"><i></i><i></i><i></i></span>
            <span class="theme-sample-workspace">
              <span class="theme-sample-heading"></span>
              <span class="theme-sample-cards"><i></i><i></i></span>
              <span class="theme-sample-action"></span>
            </span>
          </span>
          <span class="theme-option-caption">
            <strong>{{ label(theme) }}</strong>
            <small>{{ description(theme) }}</small>
          </span>
          <span v-if="savedTheme.id === theme.id" class="theme-saved-mark">
            {{ tr('Applied', 'প্রয়োগ করা') }}
          </span>
        </span>
      </label>
    </fieldset>

    <div class="theme-settings-footer">
      <span role="status" class="theme-message">{{ savedMessage }}</span>
      <div class="theme-actions">
        <button v-if="hasThemePreview" type="button" class="theme-button" @click="cancelThemePreview">
          {{ tr('Cancel preview', 'প্রিভিউ বাতিল করুন') }}
        </button>
        <button type="button" class="theme-button theme-apply" :disabled="!hasThemePreview" @click="applyTheme">
          {{ tr('Apply theme', 'থিম প্রয়োগ করুন') }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.theme-settings{padding:clamp(14px,2.4vw,22px);margin-bottom:18px;background:var(--os-surface,#fffefa);border:1px solid var(--os-border,#e5d6c4);border-radius:16px;color:var(--os-ink,#38291f)}
.theme-settings-header,.theme-settings-footer,.theme-actions{display:flex;align-items:center;flex-wrap:wrap;gap:10px 14px}
.theme-settings-header,.theme-settings-footer{justify-content:space-between}
.theme-settings-header h2{margin:0 0 3px;font-size:1.08rem;font-weight:750}
.theme-settings-header p,.theme-message{margin:0;color:var(--os-muted,#6d5b4c);font-size:.82rem}
.theme-current{background:var(--os-tint,#f3ebe0);border-radius:7px;padding:5px 9px;font-size:.76rem;font-weight:650}
.theme-options{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,155px),1fr));gap:9px;border:0;padding:0;margin:15px 0}
.theme-option{min-width:0;display:flex;position:relative;cursor:pointer}
.theme-option-body{display:flex;flex-direction:column;gap:7px;position:relative;width:100%;border:1px solid var(--os-border,#e5d6c4);border-radius:10px;padding:8px;background:var(--os-canvas,#f8f6f0)}
.theme-option:hover .theme-option-body,.theme-option input:checked + .theme-option-body{border-color:var(--os-accent,#785238)}
.theme-option input:checked + .theme-option-body{box-shadow:inset 0 0 0 1px var(--os-accent,#785238)}
.theme-option input:focus-visible + .theme-option-body,.theme-button:focus-visible{outline:2px solid var(--os-accent,#785238);outline-offset:2px}
.theme-sample{height:64px;display:grid;grid-template-columns:28% 1fr;overflow:hidden;background:var(--sample-canvas);border:1px solid var(--sample-border);border-radius:6px}
.theme-sample-nav{display:grid;align-content:start;gap:5px;padding:8px 5px;background:var(--sample-tint)}
.theme-sample-nav i{height:4px;background:var(--sample-border);border-radius:2px}
.theme-sample-nav i:first-child{background:var(--sample-accent)}
.theme-sample-workspace{min-width:0;display:grid;align-content:center;gap:4px;padding:5px 7px}
.theme-sample-heading{width:54%;height:4px;background:var(--sample-strong);border-radius:2px}
.theme-sample-cards{display:flex;gap:4px}
.theme-sample-cards i{flex:1;height:16px;border:1px solid var(--sample-border);border-radius:3px;background:var(--sample-surface)}
.theme-sample-action{width:29%;height:5px;margin-left:auto;background:var(--sample-accent);border-radius:2px}
.theme-option-caption strong,.theme-option-caption small{display:block;overflow-wrap:anywhere}
.theme-option-caption strong{font-size:.85rem;font-weight:750}
.theme-option-caption small{margin-top:2px;color:var(--os-muted,#6d5b4c);font-size:.75rem}
.theme-saved-mark{align-self:flex-start;background:var(--os-selection,#e8d9c6);border-radius:5px;padding:2px 6px;color:var(--os-strong,#644229);font-size:.69rem;font-weight:700}
.theme-actions{margin-left:auto}
.theme-button{min-height:38px;border:1px solid var(--os-border,#e5d6c4);border-radius:8px;background:var(--os-surface,#fffefa);color:var(--os-ink,#38291f);padding:6px 12px;font-size:.82rem;font-weight:650}
.theme-button.theme-apply{background:var(--os-accent,#785238);border-color:var(--os-accent,#785238);color:#fff}
.theme-button.theme-apply:hover:not(:disabled){background:var(--os-strong,#644229);border-color:var(--os-strong,#644229)}
</style>
