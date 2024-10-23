import frappe
from frappe import _
from frappe.utils import getdate, flt

def execute(filters=None):
    if not filters:
        filters = {}

    data = get_data(filters)
    columns = get_columns()
    return columns, data

def get_opening_balance(filters):
    gle = frappe.db.sql("""
                        SELECT SUM(gl.debit) AS opening_balance
                        FROM `tabGL Entry` gl
                        JOIN `tabJournal Entry` je ON gl.voucher_no = je.name
                        JOIN `tabJournal Entry Account` jea ON je.name = jea.parent
                        WHERE gl.docstatus = 1 
                        AND gl.is_cancelled = 0
                        AND gl.voucher_type = 'Journal Entry'
                        AND jea.reference_type = 'Employee Advance'
                        AND gl.posting_date < %s
                        AND gl.party = %s
                        """, (filters.get("from_date"), filters.get("employee")), as_dict=True)
    
    return gle[0].get('opening_balance') if gle else 0


def get_conditions(filters):
    cond = []
    if filters.get('from_date') and filters.get('to_date'):
        cond.append("gl.posting_date BETWEEN %s AND %s")
    if filters.get('cost_center'):
        cond.append("gl.cost_center = %s")
    if filters.get('employee'):
        cond.append("gl.party = %s")
    return ' AND '.join(cond)

def get_gl_entries(filters):
    d1 = []
    cond = get_conditions(filters)
    base_query = """
        SELECT 
            gl.voucher_type AS transaction_type, 
            gl.voucher_no AS transaction_id,
            gl.party_type, 
            gl.party,
            gl.posting_date,
            gl.debit,
            gl.credit,
            gl.account,
            gl.cost_center
        FROM `tabGL Entry` AS gl 
        WHERE gl.is_cancelled = 0 AND gl.party_type = 'Employee'
        {} 
        AND gl.voucher_type IN ('Journal Entry', 'Employee Advance Settlement')
        ORDER BY gl.party, gl.posting_date ASC
    """.format(f' AND {cond}' if cond else '')

    params = []
    if filters.get('from_date') and filters.get('to_date'):
        params.extend([filters['from_date'], filters['to_date']])
    if filters.get('cost_center'):
        params.append(filters['cost_center'])
    if filters.get('employee'):
        params.append(filters['employee'])

    query = frappe.db.sql(base_query, params, as_dict=True)

    opening_balance = get_opening_balance(filters)

    flag = 0
    temp = 0.0
    for q in query:
        if flag == 0:
            q['opening_balance'] = flt(opening_balance)
            temp = q['debit']
            d1.append(q)
            flag = 1
        else:
            q['opening_balance'] = flt(opening_balance) + temp
            d1.append(q)
            flag = 1
            temp += q['debit']
        
    return d1

def get_data(filters):
    gl_entries = get_gl_entries(filters)
    new_gle = set_expense_account(gl_entries)
    mapped_data = get_mapped_data(new_gle)
    data = get_closing_balance(mapped_data)
    return data

def get_closing_balance(mapped_data):
    data = []
    closing_balance = 0.0
    for m in mapped_data:
        m['closing_balance'] = m['opening_balance'] + m['debit'] -  m['credit']
        data.append(m)
    return data


def get_mapped_data(gl_entries):
    filtered_entries = []
    for entry in gl_entries:
        if entry['transaction_type'] == 'Journal Entry':
            query = """
                    SELECT je.name, jea.reference_name, jea.reference_type
                    FROM `tabJournal Entry` je
                    JOIN `tabJournal Entry Account` jea ON je.name = jea.parent
                    WHERE je.name = %s AND jea.reference_type in ('POL Receive','Employee Advance')
                    AND (jea.reference_name IN (SELECT ea.name FROM `tabEmployee Advance` ea WHERE ea.docstatus = 1 AND ea.advance_type='Imprest Advance') 
                         OR jea.reference_name IN (SELECT pr.name FROM `tabPOL Receive` pr WHERE pr.settle_imprest_advance=1))
                    AND je.docstatus = 1
                    """
            data = frappe.db.sql(query, entry['transaction_id'], as_dict=True)
            if data:
                entry['reference_name'] = data[0]['reference_name']
                entry['reference_type'] = data[0]['reference_type']
            else:
                continue

        elif entry['transaction_type'] == 'Employee Advance Settlement':
            query = """
                    SELECT eas.name, eas.bill_no, eas.narration, i.party
                    FROM `tabEmployee Advance Settlement` eas, `tabEmployee Advance Settlement Item` i
                    WHERE i.parent = eas.name and eas.name = %s AND eas.docstatus = 1 AND eas.advance_type = 'Project Imprest'
                    """
            data = frappe.db.sql(query, entry['transaction_id'], as_dict=True)
            if data:
                entry['reference_name'] = data[0]['name']
                entry['bill_no'] = data[0]['bill_no']
                entry['narration'] = data[0]['narration']
                entry['supplier'] = data[0]['party']
                entry['reference_type'] = 'Employee Advance Settlement'
            else:
                continue
        
        filtered_entries.append(entry)

    return filtered_entries

def set_expense_account(gl_entries):
    data1 = []
    for gle in gl_entries:
        if gle.debit:
            gle['expense_account'] = frappe.db.get_value("GL Entry", {'voucher_no': gle.transaction_id, 'credit': ('>', 0)}, 'account')
        else:
           gle['expense_account'] = frappe.db.get_value("GL Entry", {'voucher_no': gle.transaction_id, 'debit': ('>', 0)}, 'account')
        data1.append(gle)

    return data1

def get_columns():
    return [    
        {
            "label": _("Transaction Type"),
            "fieldtype": "Data",
            "fieldname": "transaction_type",
            "width": 250,
        },
        {
            "label": _("Transaction ID"),
            "fieldtype": "Data",
            "fieldname": "transaction_id",
            "fieldtype": "Dynamic Link",
            "options": "transaction_type",
            "width": 150,
        },
        {
            "label": _("Party Type"),
            "fieldtype": "Data",
            "fieldname": "party_type",
            "width": 100,
        },
        {
            "label": _("Party"),
            "fieldtype": "Dynamic Link",
            "fieldname": "party",
            "options": "party_type",
            "width": 120,
        },
        {
            "label": _("Posting Date"),
            "fieldtype": "Date",
            "fieldname": "posting_date",
            "width": 120,
        },
        {
            "label": _("Opening Balance"),
            "fieldtype": "Currency",
            "fieldname": "opening_balance",
            "width": 150,
        },
        {
            "label": _("Imprest Amount"),
            "fieldtype": "Currency",
            "fieldname": "debit",
            "width": 140,
        },
        {
            "label": _("Expense Amount"),
            "fieldtype": "Currency",
            "fieldname": "credit",
            "width": 140,
        },
        {
            "label": _("Closing Balance"),
            "fieldtype": "Currency",
            "fieldname": "closing_balance",
            "width": 150,
        },
        # {
        #     "label": _("Account"),
        #     "fieldtype": "Link",
        #     "fieldname": "account",
        #     "options": "Account",
        #     "width": 230,
        # },
        {
            "label": _("Expense Account"),
            "fieldtype": "Link",
            "fieldname": "expense_account",
            "options": "Account",
            "width": 230,
        },
        {
            "label": _("Bill No"),
            "fieldtype": "Data",
            "fieldname": "bill_no",
            "width": 80,
        },
        {
            "label": _("Supplier"),
            "fieldtype": "Link",
            "fieldname": "supplier",
            "width": 150,
            "options": "Supplier"
        },
        {
            "label": _("Cost Center"),
            "fieldtype": "Link",
            "fieldname": "cost_center",
            "width": 200,
            "options": "Cost Center"
        },
        {
            "label": _("Reference Type"),
            "fieldtype": "Data",
            "fieldname": "reference_type",
            "width": 250,
        },
        {
            "label": _("Reference Name"),
            "fieldtype": "Data",
            "fieldname": "reference_name",
            "width": 220,
        },
        {
            "label": _("Narration"),
            "fieldtype": "Small Text",
            "fieldname": "narration",
            "width": 300,
        },
        {
            "label": _("Is Subtotal"),
            "fieldtype": "Check",
            "fieldname": "is_subtotal",
            "width": 100,
            "hidden": 1  # Hide this column in the UI, used only for styling
        },
        {
            "label": _("Bold"),
            "fieldtype": "Check",
            "fieldname": "bold",
            "width": 100,
            "hidden": 1  # Hide this column in the UI, used only for styling
        },
    ]
