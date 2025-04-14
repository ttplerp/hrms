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

# def get_data(filters):
#     conditions = get_conditions(filters)
#     query = '''
#         select designation as muster_roll_designation, count(name)as count from `tabMuster Roll Employee` where status="Active" group by designation;
#     '''.format(conditions=conditions)
    
#     data = frappe.db.sql(query, as_dict=1)

#     data2 = frappe.db.sql('''
#         select count(name) as count, designation from `tabEmployee` where designation in ('Electrician','Painter');
#     ''')
#     for i in data:
#         if i['muster_roll_designation'] == 'Electrician':
#             for j in data2:
#                 if j['designation'] == i['muster_roll_designation']:
#                     i['count'] += j['count']
#             # frappe.throw(str(i['muster_roll_designation']))
#     return data
def get_data(filters):
    # Get all active muster roll employee counts grouped by designation
    muster_data = frappe.db.sql('''
        SELECT 
            designation AS muster_roll_designation, 
            COUNT(name) AS count 
        FROM 
            `tabMuster Roll Employee` 
        WHERE 
            status = "Active" 
        GROUP BY 
            designation
    ''', as_dict=True)

    # Get regular employee counts for overlapping designations (like Electrician, Painter)
    employee_data = frappe.db.sql('''
        SELECT 
            designation, 
            COUNT(name) AS count 
        FROM 
            `tabEmployee` 
        WHERE 
            designation IN ('Electrician', 'Painter','Mechanic','Plumber','Welder') 
        GROUP BY 
            designation
    ''', as_dict=True)

    # Convert employee data into a dictionary for quick access
    employee_count_map = {row["designation"]: row["count"] for row in employee_data}

    # Add employee counts to muster data if designation matches
    for row in muster_data:
        designation = row["muster_roll_designation"]
        if designation in employee_count_map:
            row["count"] += employee_count_map[designation]

    return muster_data


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
