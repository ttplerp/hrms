# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "muster_roll_designation",
            "label": "Muster Roll Designation",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "count",
            "label": "Total",
            "fieldtype": "Data",
            "width": 200
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    query = '''
        select designation as muster_roll_designation, count(name)as count from `tabMuster Roll Employee` where status="Active" group by designation;
    '''.format(conditions=conditions)
    data = frappe.db.sql(query, as_dict=1)
    return data

def get_conditions(filters):
    conditions = []
    if filters and filters.get("parent_account"):
        conditions.append("a.parent_account = '{}'".format(filters.get("parent_account")))
    if filters and filters.get("account"):
        conditions.append("a.name = '{}'".format(filters.get("account")))
    if filters and filters.get("fiscal_year"):
        conditions.append("fiscal_year = '{}'".format(filters.get("fiscal_year")))
    if filters.get("monthly"):
        conditions.append("MONTH(gl.posting_date) = '{}'".format(filters.get("monthly")))

    return "AND {}".format(" AND ".join(conditions)) if conditions else ""
