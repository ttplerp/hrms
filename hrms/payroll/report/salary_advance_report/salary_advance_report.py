# Copyright (c) 2025, Frappe Technologies Pvt. Ltd.
# For license information, please see license.txt

import frappe
from frappe import _  

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Employee",
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 150
        },
        {
            "label": "Employee Name",
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "fiscal_year",
            "label": _("Fiscal Year"),  
            "fieldtype": "Link",
            "options": "Fiscal Year",
            "width": 150
        },
        {
            "fieldname": "month",
            "label": _("Month"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Designation",
            "fieldname": "designation",
            "fieldtype": "Link",
            "options": "Designation",
            "width": 180
        },
        {
            "label": "Department",
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 180
        },
        {
            "label": "Salary Component",
            "fieldname": "salary_component",
            "fieldtype": "Link",
            "options": "Salary Component",
            "width": 200
        },
        {
            "label": "Deduction Amount",
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 150
        },
    ]


def get_data(filters):
    conditions = ""
    values = {}

    if filters.get("employee"):
        conditions += " AND ss.employee = %(employee)s"
        values["employee"] = filters.get("employee")

    query = f"""
        SELECT 
            ss.employee,
            ss.employee_name,
            ss.designation,
            ss.department,
            ss.fiscal_year,
            sd.salary_component,
            sd.amount,
            ss.start_date,
            ss.name as salary_slip
        FROM `tabSalary Slip` ss
        INNER JOIN `tabSalary Detail` sd 
            ON ss.name = sd.parent
        WHERE sd.salary_component = 'Salary Advance Deductions'
          AND ss.docstatus = 1
          {conditions}
    """

    data = frappe.db.sql(query, values, as_dict=1)

    month_map = {
        1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
        7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"
    }

    for row in data:
        if row.get("start_date"):
            month_num = row["start_date"].month
            row["month"] = month_map.get(month_num, "")
        else:
            row["month"] = ""

    return data
