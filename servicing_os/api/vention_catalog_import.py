# SERVICING OS VENTION Catalog Import - September 2026
# Bench-only administrative functions; intentionally NOT whitelisted.
# Source: verified supplied PDF. Conflict ALABAF withheld.
import json
import frappe

COMPANY = 'AL MODINA COMPUTERS LIMITED'
CURRENCY = 'BDT'
BUYING = 'Standard Buying'
SELLING = 'Standard Selling'
ROOT = 'VENTION Products'

def _load_rows():
    from pathlib import Path
    path = Path(__file__).with_name('vention_catalog_2026_09.json')
    rows = json.loads(path.read_text(encoding='utf-8'))
    codes = [r['sku'] for r in rows]
    if len(rows) != 418 or len(set(codes)) != 418:
        frappe.throw('Catalog integrity failure: expected exactly 418 unique approved rows.')
    if any(r['model'] == 'ALABAF' for r in rows):
        frappe.throw('Conflicting ALABAF model must stay excluded.')
    for row in rows:
        if row['sku'] != 'VENTION-' + row['model'] or row['selling'] != row['dp'] + 100:
            frappe.throw('Catalog validation failed on row ' + str(row.get('sl')))
    return rows

def _preflight():
    if not frappe.db.exists('Company', COMPANY):
        frappe.throw('Company not found: ' + COMPANY)
    if frappe.db.get_value('Company', COMPANY, 'default_currency') != CURRENCY:
        frappe.throw('Company currency is not BDT. Refusing to import BDT prices.')
    if not frappe.db.exists('UOM', 'Nos'):
        frappe.throw('Stock UOM Nos is missing.')
    if frappe.db.get_default('item_naming_by') == 'Naming Series':
        frappe.throw('Item naming uses Naming Series; this importer needs Item Code naming for VENTION-Model SKUs.')
    for label, flag in ((BUYING, 'buying'), (SELLING, 'selling')):
        price = frappe.db.get_value('Price List', label, ['currency','enabled','buying','selling'], as_dict=True)
        if not price or not price.enabled or price.currency != CURRENCY or not price.get(flag):
            frappe.throw('Price List ' + label + ' must be enabled for ' + flag + ' in BDT.')
    if not frappe.db.exists('Item Group','All Item Groups') or not frappe.db.get_value('Item Group','All Item Groups','is_group'):
        frappe.throw('Root Item Group All Item Groups is missing/not a group. No groups created.')
    rows=_load_rows()
    existing=sum(bool(frappe.db.exists('Item', r['sku'])) for r in rows)
    return {'company':COMPANY,'currency':CURRENCY,'approved_models':len(rows),'existing_skus':existing,'new_skus':len(rows)-existing,'warranty_365_days':sum(bool(r.get('warranty_days')) for r in rows),'source_duplicate_rows_skipped':2,'source_conflict_rows_skipped':2,'buying_price_list':BUYING,'selling_price_list':SELLING,'stock_created':0}

def check_catalog():
    return _preflight()

def _ensure_brand():
    if not frappe.db.exists('Brand','VENTION'):
        frappe.get_doc({'doctype':'Brand','brand':'VENTION'}).insert(ignore_permissions=True)

def _ensure_groups(rows):
    if not frappe.db.exists('Item Group', ROOT):
        frappe.get_doc({'doctype':'Item Group','item_group_name':ROOT,'parent_item_group':'All Item Groups','is_group':1}).insert(ignore_permissions=True)
    if not frappe.db.get_value('Item Group',ROOT,'is_group'):
        frappe.throw(ROOT + ' already exists but is not a Group')
    for group in sorted({r['category'] for r in rows}):
        if not frappe.db.exists('Item Group',group):
            frappe.get_doc({'doctype':'Item Group','item_group_name':group,'parent_item_group':ROOT,'is_group':0}).insert(ignore_permissions=True)
        elif frappe.db.get_value('Item Group',group,'parent_item_group') != ROOT:
            frappe.throw('Conflicting Item Group parent for '+group)

def _ensure_item(r, days):
    code = r['sku']
    if frappe.db.exists('Item',code):
        existing = frappe.db.get_value('Item',code,['brand','item_group','is_stock_item'],as_dict=True)
        if existing.brand != 'VENTION' or not existing.is_stock_item:
            frappe.throw('Existing SKU collision: ' + code + ' has a different brand/type.')
        return False
    full_name=r['description'].strip()
    doc={'doctype':'Item', 'item_code':code, 'item_name':full_name[:140], 'description':full_name,
         'brand':'VENTION', 'item_group':r['category'], 'stock_uom':'Nos',
         'is_stock_item':1, 'is_sales_item':1, 'is_purchase_item':1, 'has_serial_no':0,
         'include_item_in_manufacturing':0, 'opening_stock':0, 'standard_rate':0}
    if days:
        doc['warranty_period']=str(days)
    frappe.get_doc(doc).insert(ignore_permissions=True)
    return True

def _price_for(code,listname):
    entries=frappe.get_all('Item Price',filters={'item_code':code,'price_list':listname},fields=['name','uom','customer','supplier','price_list_rate'],limit_page_length=100)
    return next((d for d in entries if not d.get('customer') and not d.get('supplier') and d.get('uom') in (None,'','Nos')),None)

def _set_price(code, listname, amount, overwrite=False):
    old=_price_for(code,listname)
    if old:
        if overwrite and float(old.price_list_rate) != float(amount):
            doc=frappe.get_doc('Item Price',old.name)
            doc.price_list_rate=amount
            doc.save(ignore_permissions=True)
            return 'updated'
        return 'untouched'
    frappe.get_doc({'doctype':'Item Price','item_code':code,'price_list':listname,
         'price_list_rate':amount,'uom':'Nos','currency':CURRENCY}).insert(ignore_permissions=True)
    return 'created'

def apply_catalog(default_warranty_days=0, overwrite_prices=False):
    days_default=int(default_warranty_days or 0)
    if days_default not in (0,30,90,180,365,730,1095):
        frappe.throw('Warranty days must be one of 0,30,90,180,365,730,1095 (0=source only).')
    if str(overwrite_prices).lower() not in ('false','0','true','1'):
        frappe.throw('overwrite_prices must be true or false.')
    overwrite=str(overwrite_prices).lower() in ('true','1')
    result=_preflight()
    rows=_load_rows()
    tally={'items_created':0,'existing_items_reused':0,'buying_prices_created':0,
           'selling_prices_created':0,'prices_updated':0,'prices_existing_untouched':0,
           'warranty_items_created':0}
    try:
        _ensure_brand()
        _ensure_groups(rows)
        for r in rows:
            try:
                warranty_days=r.get('warranty_days') or days_default
                is_new=_ensure_item(r,warranty_days)
                tally['items_created' if is_new else 'existing_items_reused'] += 1
                if is_new and warranty_days:
                    tally['warranty_items_created'] += 1
                for label,amount,prefix in ((BUYING,r['dp'],'buying'),(SELLING,r['selling'],'selling')):
                    outcome=_set_price(r['sku'],label,amount,overwrite=overwrite)
                    if outcome == 'created':
                        tally[prefix+'_prices_created']+=1
                    elif outcome == 'updated':
                        tally['prices_updated']+=1
                    else:
                        tally['prices_existing_untouched']+=1
            except Exception as e:
                frappe.throw('Import failed on source SL '+str(r['sl'])+' ('+r['sku']+'): '+str(e))
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise
    result.update(tally)
    result.update({'source':'VENTION Price List September 2026','conflicted_model_excluded':'ALABAF',
                   'default_warranty_days_for_unspecified':days_default,
                   'prices_overwrite_authorized':overwrite,
                   'stock_created':0,'financial_documents_created':0})
    return result
