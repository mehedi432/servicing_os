"""SERVICING OS retail counter customer picker.

Uses standard Customer, Contact and Address records.
"""
import re
import frappe


def _require(right):
    if not frappe.has_permission('Customer', ptype=right):
        frappe.throw('Customer ' + right + ' permission required.', frappe.PermissionError)


def _phone(value):
    digits = re.sub(r'\D', '', str(value or ''))
    if len(digits) == 13 and digits.startswith('8801'):
        digits = '0' + digits[3:]
    if len(digits) == 11 and digits.startswith('01') and digits[2] in '3456789':
        return digits
    return None


def _variants(phone):
    return [phone, '+88' + phone, '88' + phone]


def _leaf_names(doctype):
    return frappe.get_all(doctype, filters={'is_group': 0}, pluck='name', order_by='name asc', limit_page_length=200)


def _suggest(options, preferred):
    for value in preferred:
        if value in options:
            return value
    return options[0] if len(options) == 1 else ''


@frappe.whitelist(methods=['GET'])
def get_customer_config():
    _require('read')
    groups = _leaf_names('Customer Group')
    territories = _leaf_names('Territory')
    sales_territory = frappe.db.get_single_value('Selling Settings', 'territory')
    default_territory = sales_territory if sales_territory in territories else _suggest(
        territories, ('Bangladesh', 'Bangladesh Territory')
    )
    return {
        'groups': groups,
        'territories': territories,
        'default_group': _suggest(groups, ('Individual', 'Retail', 'Retail Customers')),
        'default_territory': default_territory,
        'can_create': bool(frappe.has_permission('Customer', ptype='create')),
        'mobile_required': True,
    }


def customer_address_fields(address_line1=None, city=None, pincode=None):
    address = {key: str(value or '').strip() for key, value in
               (('address_line1', address_line1), ('city', city), ('pincode', pincode))}
    if not any(address.values()):
        return None
    if not address['address_line1'] or not address['city']:
        frappe.throw('Enter the customer address and city or upazila.')
    for key, length in (('address_line1', 140), ('city', 140), ('pincode', 20)):
        if len(address[key]) > length:
            frappe.throw('Check the address length. Address and city allow 140 characters, and postal code allows 20.')
    address['country'] = frappe.db.get_single_value('System Settings', 'country') or 'Bangladesh'
    if not frappe.db.exists('Country', address['country']):
        frappe.throw('Set a valid country in System Settings before saving a customer address.')
    if not frappe.has_permission('Address', ptype='create'):
        frappe.throw('Address create permission is required to save the customer address.', frappe.PermissionError)
    return address


def save_customer_address(customer, fields):
    address = frappe.get_doc({
        'doctype': 'Address',
        **fields,
        'address_title': customer.customer_name,
        'address_type': 'Billing',
        'is_primary_address': 1,
        'links': [{'link_doctype': 'Customer', 'link_name': customer.name}],
    })
    address.insert()
    # This customer was created in the same request. Set its link without requiring a second Customer permission.
    customer.db_set('customer_primary_address', address.name)


def _linked_customers_for_contact(contact_names):
    if not contact_names:
        return []
    return frappe.get_all('Dynamic Link', filters={
        'parenttype': 'Contact',
        'parent': ['in', list(contact_names)],
        'link_doctype': 'Customer',
    }, pluck='link_name', limit_page_length=200)


def _phone_customer_names(phone, partial=False):
    """Find matches in both Customer.mobile_no and linked Contact phones."""
    if partial:
        needle = re.sub(r'\D', '', str(phone or ''))[-8:]
        if len(needle) < 4:
            return set()
        filter_value = ['like', '%' + needle + '%']
    else:
        filter_value = ['in', _variants(phone)]

    names = set(frappe.get_all('Customer',
        filters={'mobile_no': filter_value}, pluck='name', limit_page_length=100))
    contacts = set(frappe.get_all('Contact',
        filters={'mobile_no': filter_value}, pluck='name', limit_page_length=100))
    # Contact phone children may hold a number not cached in Contact.mobile_no.
    contacts.update(frappe.get_all('Contact Phone',
        filters={'phone': filter_value}, pluck='parent', limit_page_length=100))
    names.update(_linked_customers_for_contact(contacts))
    return names


@frappe.whitelist(methods=['GET'])
def search_customers(search=''):
    _require('read')
    text = str(search or '').strip()[:100]
    if not text:
        return {'customers': []}
    escaped = text.replace('\\', '\\\\').replace('%', r'\%').replace('_', r'\_')
    rows = frappe.get_list('Customer', filters={'disabled': 0},
        or_filters=[
            ['Customer', 'customer_name', 'like', '%' + escaped + '%'],
            ['Customer', 'name', 'like', '%' + escaped + '%'],
            ['Customer', 'mobile_no', 'like', '%' + escaped + '%'],
        ], fields=['name', 'customer_name', 'mobile_no'],
        order_by='customer_name asc', limit_page_length=20)
    found = {r.name: r for r in rows}
    if re.search(r'\d', text):
        for name in _phone_customer_names(text, partial=True):
            if name not in found and len(found) < 30 and frappe.has_permission('Customer', 'read', name):
                doc = frappe.db.get_value('Customer', name,
                    ['name', 'customer_name', 'mobile_no', 'disabled'], as_dict=True)
                if doc and not doc.disabled:
                    found[name] = doc
    return {'customers': [
        {'name': r.name, 'customer_name': r.customer_name,
         'mobile': r.mobile_no or ''}
        for r in list(found.values())[:30]
    ]}


@frappe.whitelist(methods=['POST'])
def create_counter_customer(customer_name, mobile_no, customer_group=None, territory=None,
                            address_line1=None, city=None, pincode=None):
    _require('read')
    _require('create')
    name = ' '.join(str(customer_name or '').strip().split())
    if not 2 <= len(name) <= 120:
        frappe.throw('Enter the customer name (2–120 characters).')
    number = _phone(mobile_no)
    if not number:
        frappe.throw('Enter a valid Bangladesh mobile number, e.g. 01XXXXXXXXX.')

    matched = _phone_customer_names(number, partial=False)
    # Also detect numbers with spaces or hyphens in existing Contact records.
    matched.update(_phone_customer_names(number[-8:], partial=True))
    for existing_name in sorted(matched):
        existing = frappe.db.get_value('Customer', existing_name,
            ['name', 'mobile_no', 'disabled'], as_dict=True)
        if existing and not existing.disabled:
            contact_numbers = []
            if _phone(existing.mobile_no) != number:
                linked = frappe.get_all('Dynamic Link', filters={
                    'parenttype': 'Contact', 'link_doctype': 'Customer',
                    'link_name': existing_name}, pluck='parent', limit_page_length=40)
                if linked:
                    contact_numbers.extend(frappe.get_all('Contact', filters={
                        'name': ['in', linked]}, pluck='mobile_no', limit_page_length=40))
                    contact_numbers.extend(frappe.get_all('Contact Phone', filters={
                        'parent': ['in', linked]}, pluck='phone', limit_page_length=100))
            if _phone(existing.mobile_no) == number or any(_phone(n) == number for n in contact_numbers):
                frappe.throw('This mobile number already belongs to an existing customer. Search and select that customer instead.')

    cfg = get_customer_config()
    group = str(customer_group or cfg['default_group'] or '').strip()
    place = str(territory or cfg['default_territory'] or '').strip()
    if group not in cfg['groups']:
        frappe.throw('Select a valid Customer Group.')
    if place not in cfg['territories']:
        frappe.throw('Set a default leaf Territory in Selling Settings before adding customers.')
    address = customer_address_fields(address_line1, city, pincode)

    first, _, last = name.partition(' ')
    details = {
        'doctype': 'Customer', 'customer_name': name,
        'customer_type': 'Individual', 'customer_group': group,
        'territory': place, 'mobile_no': number,
    }
    meta = frappe.get_meta('Customer')
    if meta.has_field('first_name'):
        details['first_name'] = first
    if meta.has_field('last_name') and last:
        details['last_name'] = last
    customer = frappe.get_doc(details)
    customer.insert()  # standard permissions and validations; no ignore_permissions
    customer.reload()

    contact_name = customer.get('customer_primary_contact')
    if not contact_name:
        # Some installations don't automatically generate the linked Contact.
        if not frappe.has_permission('Contact', ptype='create'):
            frappe.throw('Contact create permission is needed to save the mobile number.')
        contact = frappe.get_doc({
            'doctype': 'Contact', 'first_name': first, 'last_name': last,
            'is_primary_contact': 1,
            'phone_nos': [{'phone': number, 'is_primary_mobile_no': 1}],
            'links': [{'link_doctype': 'Customer', 'link_name': customer.name}],
        })
        contact.insert()
        customer.customer_primary_contact = contact.name
        customer.save()
        contact_name = contact.name

    # Confirm that the new customer's primary Contact really contains the phone.
    contact = frappe.get_doc('Contact', contact_name)
    recorded_numbers = [p.phone for p in (contact.get('phone_nos') or [])]
    if not any(_phone(x) == number for x in [contact.get('mobile_no')] + recorded_numbers):
        if not frappe.has_permission('Contact', ptype='write'):
            frappe.throw('Contact write permission required to save the mobile number.')
        contact.append('phone_nos', {'phone': number, 'is_primary_mobile_no': 1})
        contact.save()
        contact.reload()
        if not any(_phone(p.phone) == number for p in contact.get('phone_nos') or []):
            frappe.throw('Mobile number could not be stored in the primary Contact.')

    if address:
        save_customer_address(customer, address)

    # No explicit commit: the framework commits a successful POST transaction.
    return {'success': True, 'customer': {
        'name': customer.name, 'customer_name': customer.customer_name,
        'mobile': number, 'contact': contact_name,
        'address': address,
    }}
