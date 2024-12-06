# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe


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
            "fieldname": "gender",
            "label": "Gender",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "fieldname": "total",
            "label": "Total",
            "fieldtype": "Data",
            "width": 250
        },
       
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    result = {}
   
    query = '''
       select count(name) as total, gender from `tabEmployee` where status="Active" group by gender;
    '''
    data = frappe.db.sql(query, as_dict=1)
    for i in data:
        if i.gender not in result:
            result[i.gender]= {'gender':i.gender,'total':i.total}
    query2='''
		select count(name) as total, gender from `tabMuster Roll Employee` where status="Active" group by gender;
    '''
    data2 = frappe.db.sql(query2, as_dict=1)
    for i in data2:
        if i.gender not in result:
            result[i.gender]= {'gender':i.gender,'total':i.total}
        else:
            result[i.gender]['total'] += i.total
    # frappe.throw(str(list(result.values())))
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
    if filters.get("cost_center"):
        conditions.append("gl.cost_center = '{}'".format(filters.get("cost_center")))

    return "AND {}".format(" AND ".join(conditions)) if conditions else ""

