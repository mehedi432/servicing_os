import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { encodeInvoiceBarcode, encodeInvoiceQr, INVOICE_PRINT_FORMATS, invoicePrintBrand, invoicePrintHtml } from '../src/components/invoice-print.mjs'

const stylesheet = readFileSync(new URL('../src/components/invoice-paper.css', import.meta.url), 'utf8')

test('the same document and stylesheet are used for each printable format', () => {
  assert.deepEqual(INVOICE_PRINT_FORMATS.map(({ id }) => id), ['a4', 'a5', 'thermal', 'delivery'])
  for (const { id, page, margin } of INVOICE_PRINT_FORMATS) {
    const markup = '<article class="invoice-paper">Invoice sample</article>'
    const output = invoicePrintHtml(markup, stylesheet, id)
    assert.ok(output.includes(`@page{size:${page};margin:${margin}}`))
    assert.ok(output.includes(stylesheet))
    assert.ok(output.includes(`<body>${markup}</body>`))
  }
  assert.throws(() => invoicePrintHtml('', '', 'unknown'), RangeError)
})

test('QR and barcode preserve scan space and skip invalid or oversized input', () => {
  const invoice = 'ACC-SINV-2026-00432'
  const qr = encodeInvoiceQr(invoice)
  assert.ok(qr.size >= 29 && qr.path.startsWith('M4 4'))
  assert.equal(encodeInvoiceQr(' — '), null)

  for (const { id } of INVOICE_PRINT_FORMATS) {
    const barcode = encodeInvoiceBarcode(invoice, id)
    assert.ok(barcode.path.startsWith('M12 0'))
  }
  assert.equal(encodeInvoiceBarcode('Ñ', 'a4'), null)
  assert.equal(encodeInvoiceBarcode('A'.repeat(65), 'thermal'), null)
})

test('saved company branding takes precedence for all print formats', () => {
  assert.deepEqual(invoicePrintBrand({ company: 'Example Company' }), {
    name: 'Example Company', address: '', contact: [],
  })
  assert.deepEqual(invoicePrintBrand({
    company: 'AL MODINA COMPUTERS LIMITED', company_address: 'Recorded address', company_phone: '0123',
  }), { name: 'AL MODINA COMPUTERS LIMITED', address: 'Recorded address', contact: ['0123'] })
})
