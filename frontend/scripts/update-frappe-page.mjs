import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '..'
)

const appRoot = path.resolve(root, '../servicing_os')

const manifestPath = path.join(
  appRoot, 'public/frontend/.vite/manifest.json'
)

const templatePath = path.join(
  appRoot, 'www/servicing-os.html'
)

const manifest = JSON.parse(
  fs.readFileSync(manifestPath, 'utf8')
)

const entry = manifest['index.html']

if (!entry?.file) {
  throw new Error('Vite entry not found in manifest')
}

const base = '/assets/servicing_os/frontend/'

const cssTags = (entry.css || [])
  .map(file =>
    `<link rel="stylesheet" href="${base}${file}">`
  )
  .join('\n')

const jsTag =
  `<script type="module" src="${base}${entry.file}"></script>`

const template = `{% extends "templates/web.html" %}
{% block page_content %}

<style>
html, body {
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
  min-height: 100% !important;
  overflow-x: hidden;
}

.navbar, .web-footer, body > footer {
  display: none !important;
}

.container, .page-container, .page-content,
.page_content, .web-page, .main-section,
main, #page-servicing-os {
  width: 100% !important;
  max-width: none !important;
  margin: 0 !important;
  padding: 0 !important;
}

#app {
  width: 100%;
  min-height: 100vh;
}
</style>

${cssTags}

<div id="app"></div>

${jsTag}

{% endblock %}
`

fs.writeFileSync(templatePath, template)

console.log('SERVICING OS page updated successfully')
console.log('JavaScript:', base + entry.file)
console.log('CSS:', entry.css || [])
