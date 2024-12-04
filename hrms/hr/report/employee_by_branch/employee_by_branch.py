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
            "fieldname": "branch",
            "label": "Branch",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "Contract",
            "label": "Contract",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "Regular",
            "label": "Regular",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "Muster Roll",
            "label": "Muster Roll",
            "fieldtype": "Data",
            "width": 200
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    query = '''
       select count(name) as count, branch,employment_type from `tabEmployee` where status="Active" group by employment_type,branch ;
    '''.format(conditions=conditions)
    data = frappe.db.sql(query, as_dict=1)
    
    result = {}
    
    for row in data:
        if row['branch'] not in result:
            result[row['branch']] = {'branch':row['branch']}
        result[row['branch']][row['employment_type']] = row['count']
    
    query2 = '''
        select count(name) as count,branch from `tabMuster Roll Employee` where status="Active" group by branch;
    '''.format(conditions=conditions)
    data2 = frappe.db.sql(query2, as_dict=1)
    
    for row in data2:
        if row['branch'] not in result:
            result[row['branch']] = {'branch':row['branch']}
        result[row['branch']]['Muster Roll'] = row['count']
        
  
    return list(result.values())

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
