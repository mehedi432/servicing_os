import JsBarcode from 'jsbarcode'
import QRCode from 'qrcode'

export const INVOICE_PRINT_FORMATS = [
  { id: 'a4', label: 'A4', size: '210 × 297 mm', page: 'A4', margin: '10mm', barcodeLimit: 330 },
  { id: 'a5', label: 'A5', size: '148 × 210 mm', page: 'A5', margin: '10mm', barcodeLimit: 285 },
  { id: 'thermal', label: '80 mm Thermal', size: 'Receipt roll', page: 'auto', margin: '0', barcodeLimit: 265 },
  { id: 'delivery', label: 'Delivery Note', size: 'A4 · No prices', page: 'A4', margin: '10mm', barcodeLimit: 330 },
]

export function invoicePrintBrand(receipt) {
  const name = receipt.company || 'AL MODINA COMPUTERS LTD'
  // Legacy Al Modina records may predate the shop's saved contact settings.
  const isAlModina = /^AL MODINA COMPUTERS (?:LTD|LIMITED)$/i.test(name)
  const address = receipt.company_address || (isAlModina ? 'Mawna Chowrasta, Sreepur, Gazipur, Bangladesh' : '')
  const phone = receipt.company_phone || (isAlModina ? '+8801911179837' : '')
  return { name, address, contact: [phone, receipt.company_email, receipt.company_website].filter(Boolean) }
}

function formatSettings(id) {
  const format = INVOICE_PRINT_FORMATS.find(option => option.id === id)
  if (!format) throw new RangeError('Unsupported invoice paper format')
  return format
}

export function encodeInvoiceQr(value) {
  const reference = String(value || '').trim()
  if (!reference || reference === '—') return null
  try {
    const { modules } = QRCode.create(reference, { errorCorrectionLevel: 'M' })
    // Include four white modules on each side for reliable scanning.
    const path = []
    for (let row = 0; row < modules.size; row += 1) {
      for (let col = 0; col < modules.size; col += 1) {
        if (modules.get(row, col)) path.push(`M${col + 4} ${row + 4}h1v1h-1z`)
      }
    }
    return { path: path.join(''), size: modules.size + 8 }
  } catch {
    return null
  }
}

export function encodeInvoiceBarcode(reference, paper) {
  if (!reference || !/^[ -~]{1,70}$/.test(reference)) return null
  try {
    const encoded = {}
    JsBarcode(encoded, reference, { format: 'CODE128', displayValue: false })
    const modules = encoded.encodings.map(part => part.data).join('')
    const size = modules.length + 24
    if (size > formatSettings(paper).barcodeLimit) return null
    const path = []
    for (const match of modules.matchAll(/1+/g)) {
      const width = match[0].length
      path.push(`M${match.index + 12} 0h${width}v48h-${width}z`)
    }
    return { path: path.join(''), size }
  } catch {
    return null
  }
}

// The caller passes the rendered InvoiceDocument markup and its own stylesheet.
export function invoicePrintHtml(markup, stylesheet, paper) {
  const { page, margin } = formatSettings(paper)
  return `<!doctype html><html><head><meta charset="utf-8"><title>Invoice</title><style>${stylesheet}
@page{size:${page};margin:${margin}} html,body{margin:0;background:white}
body .invoice-paper{margin:0;min-height:0;box-shadow:none;width:100%;max-width:none;padding:0}
body .invoice-paper.ip-thermal{width:76mm;padding:2mm}
@media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
</style></head><body>${markup}</body></html>`
}
