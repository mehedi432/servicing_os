"""SERVICING OS quotation line grid using ERPNext native Quotation documents.

No direct SQL writes, no invoice or stock postings, and no ignore_permissions.
"""
import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_days, escape_html
from servicing_os.api.sales_center import _check, _shop

COMPANY = 'AL MODINA COMPUTERS LIMITED'


def _rows(items):
    if isinstance(items, str):
        items = frappe.parse_json(items)
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        frappe.throw(_('A quotation requires 1–100 item rows.'))
    cfg = _shop()
    out = []
    for i, raw in enumerate(items):
        if not isinstance(raw, dict):
            frappe.throw(_('Invalid item row.'))
        code = str(raw.get('item_code') or '').strip()
        if len(code) > 140 or not code:
            frappe.throw(_('Please select a valid item.'))
        item = frappe.get_doc('Item', code)
        item.check_permission('read')
        if item.disabled or not item.is_sales_item:
            frappe.throw(_('Item {0} is not available for sales.').format(code))
        qty, unit_rate, discount = (flt(raw.get('qty'), 4), flt(raw.get('rate'), 4),
                                    flt(raw.get('discount_percentage'), 4))
        if not (0 < qty <= 100000 and 0 <= unit_rate <= 100000000 and 0 <= discount <= 100):
            frappe.throw(_('Invalid quantity, rate or discount on row {0}.').format(i + 1))
        uom = str(raw.get('uom') or item.stock_uom)
        if uom != item.stock_uom:
            # This compact grid does not calculate alternate UOM conversions.
            frappe.throw(_('Use the stock UOM ({0}) for item {1}.').format(item.stock_uom, code))
        out.append({'item_code':code, 'item_name':item.item_name,
                    'qty':qty, 'uom':item.stock_uom,'conversion_factor':1,
                    'price_list_rate':unit_rate,'rate':round(unit_rate*(1-discount/100),4),
                    'discount_percentage':discount,
                    'warehouse':cfg['warehouse']})
    return out


def _customer(customer):
    _check('Customer','read')
    if not customer or not frappe.db.exists('Customer', customer):
        frappe.throw(_('Select an existing customer first.'))
    if not frappe.has_permission('Customer','read',customer):
        frappe.throw(_('Customer access denied.'), frappe.PermissionError)


def _date(valid_till):
    d = getdate(valid_till) if valid_till else add_days(nowdate(),14)
    if d < getdate(nowdate()):
        frappe.throw(_('Quote validity date cannot be in the past.'))
    return d


@frappe.whitelist(methods=['GET'])
def detail(name):
    _check('Quotation','read')
    doc = frappe.get_doc('Quotation',name)
    doc.check_permission('read')
    if doc.company != COMPANY or doc.quotation_to != 'Customer':
        frappe.throw(_('Quotation is not a customer quotation for this company.'), frappe.PermissionError)
    return {'name':doc.name, 'docstatus':doc.docstatus,'customer':doc.party_name,
            'customer_name':frappe.db.get_value('Customer',doc.party_name,'customer_name') or doc.party_name,
            'valid_till':str(doc.valid_till or ''),
            'terms': doc.terms or '', 'grand_total':flt(doc.grand_total),
            'currency':doc.currency, 'items':[
                {'item_code':it.item_code,'item_name':it.item_name,'qty':flt(it.qty),
                 'uom':it.uom,'rate':flt(it.price_list_rate or it.rate),'discount_percentage':flt(it.discount_percentage),
                 'amount':flt(it.amount)} for it in doc.items]}


@frappe.whitelist(methods=['POST'])
def save(name=None, customer=None, items=None, valid_till=None, notes=None):
    _customer(customer)
    cfg = _shop()
    date = _date(valid_till)
    mapped = _rows(items)
    notes = str(notes or '')[:3000]
    if name:
        _check('Quotation','write')
        doc = frappe.get_doc('Quotation',name)
        doc.check_permission('write')
        if doc.company != COMPANY or doc.docstatus != 0 or doc.quotation_to != 'Customer':
            frappe.throw(_('Only an existing company customer-quotation draft can be edited.'))
        # Keep original taxes, price-list configuration, and other ERPNext settings.
        doc.party_name = customer
        doc.valid_till = date
        doc.set('items',mapped)
        if notes:
            doc.terms = '<p>' + escape_html(notes).replace('\n','<br>') + '</p>'
        doc.save()
    else:
        _check('Quotation','create')
        doc = frappe.get_doc({'doctype':'Quotation', 'quotation_to':'Customer',
                              'company':cfg['company'], 'party_name':customer,
                              'transaction_date':nowdate(), 'valid_till':date,
                              'selling_price_list':cfg['price_list'],
                              'items':mapped})
        if notes:
            doc.terms = '<p>' + escape_html(notes).replace('\n','<br>') + '</p>'
        doc.insert()
    return {'name':doc.name, 'status':doc.status, 'grand_total':flt(doc.grand_total),
            'net_total':flt(doc.net_total), 'currency':doc.currency, 'docstatus':doc.docstatus}
