# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    data = get_data(filters)
    columns = get_columns()
    return columns, data

def get_conditions(filters):
    cond = ''
    if filters.get('from_date') and filters.get('to_date'):
        cond += " AND gl.posting_date BETWEEN '{}' AND '{}'".format(filters['from_date'], filters['to_date'])
    if filters.get('cost_center'):
        cond += " AND gl.cost_center = '{}'".format(filters['cost_center'])
    if filters.get('employee'):
        cond += " AND gl.party = '{}'".format(filters['employee'])
    return cond

def get_gl_entries(filters):
    cond = get_conditions(filters)
    query = """
        SELECT 
            gl.voucher_type AS transaction_type, 
            gl.voucher_no AS transaction_id,
            gl.party_type, 
            gl.party,
            gl.posting_date,
            gl.debit,
            gl.credit,
            gl.account,
            gl.against,
            gl.cost_center,
            (SELECT SUM(gl2.debit - gl2.credit) FROM `tabGL Entry` gl2 
             WHERE gl2.party = gl.party AND gl2.posting_date < gl.posting_date) AS opening_balance
        FROM `tabGL Entry` AS gl 
        WHERE gl.is_cancelled = 0 AND gl.party_type = 'Employee' {}
        ORDER BY gl.party, gl.posting_date ASC
    """.format(cond)
    return frappe.db.sql(query, as_dict=True)

def add_subtotal_row(data, group_entries, group_by_field, group_by_value, opening_balance, closing_balance):
    total_debit = sum(d['debit'] for d in group_entries if d['party'])
    total_credit = sum(d['credit'] for d in group_entries if d['party'])
    
    # Add subtotal row if there are valid group_entries
    if group_entries:
        data.append({
            group_by_field: group_by_value,
            "transaction_type": "",
            "transaction_id": "",
            "party_type": "",
            "posting_date": "",
            "opening_balance": opening_balance,
            "debit": total_debit,
            "credit": total_credit,
            "closing_balance": closing_balance,
            "account": "",
            "cost_center": "",
            "reference_type": "",
            "reference_name": "",
            "is_subtotal": 1,
            "bold": 1,
        })

        # Add empty row after subtotal
        # data.append({
        #     "is_subtotal": 0,  # Flag for empty row
        #     "bold": 0,
        # })

def calculate_balances(gl_entries):
    current_party = None
    opening_balance = 0
    party_entries = []
    result = []
    
    for entry in gl_entries:
        if entry['party']:  # Only process if party is not None or empty
            if current_party != entry['party']:
                if current_party is not None:
                    # Calculate closing balance for the last set of entries
                    closing_balance = opening_balance + sum((d['debit'] or 0) - (d['credit'] or 0) for d in party_entries if d['party'])
                    add_subtotal_row(result, party_entries, 'party', current_party, opening_balance, closing_balance)
                    party_entries = []
                current_party = entry['party']
                opening_balance = entry['opening_balance'] or 0  # Initialize to 0 if None
            
            entry['opening_balance'] = opening_balance
            entry['closing_balance'] = opening_balance + (entry['debit'] or 0) - (entry['credit'] or 0)
            opening_balance = entry['closing_balance']
            
            party_entries.append(entry)
            result.append(entry)
    
    if current_party is not None:
        # Calculate closing balance for the last set of entries
        closing_balance = opening_balance + sum((d['debit'] or 0) - (d['credit'] or 0) for d in party_entries if d['party'])
        add_subtotal_row(result, party_entries, 'party', current_party, opening_balance, closing_balance)
    
    return result

def get_data(filters):
    gl_entries = get_gl_entries(filters)
    data = calculate_balances(gl_entries)
    return data

def get_columns():
    return [    
        {
            "label": _("Transaction Type"),
            "fieldtype": "Data",
            "fieldname": "transaction_type",
            "width": 150,
        },
        {
            "label": _("Transaction ID"),
            "fieldtype": "Data",
            "fieldname": "transaction_id",
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
            "fieldtype": "Data",
            "fieldname": "party",
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
            "label": _("Debit"),
            "fieldtype": "Currency",
            "fieldname": "debit",
            "width": 120,
        },
        {
            "label": _("Credit"),
            "fieldtype": "Currency",
            "fieldname": "credit",
            "width": 120,
        },
        {
            "label": _("Closing Balance"),
            "fieldtype": "Currency",
            "fieldname": "closing_balance",
            "width": 150,
        },
        {
            "label": _("Account"),
            "fieldtype": "Link",
            "fieldname": "account",
            "options": "Account",
            "width": 230,
        },
        {
            "label": _("Against Account"),
            "fieldtype": "Link",
            "fieldname": "against",
            "options": "Account",
            "width": 230,
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
            "width": 120,
        },
        {
            "label": _("Reference Name"),
            "fieldtype": "Data",
            "fieldname": "reference_name",
            "width": 120,
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
