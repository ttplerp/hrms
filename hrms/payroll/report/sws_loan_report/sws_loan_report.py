# Copyright (c) 2025, Frappe Technologies Pvt. Ltd.
# For license information, please see license.txt

import frappe
from frappe import _  # For translations

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
            "width": 100
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

    if filters.get("month"):
        # Convert month abbreviation to number
        month_map_rev = {
            "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5,
            "JUN": 6, "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10,
            "NOV": 11, "DEC": 12
        }
        month_num = month_map_rev.get(filters.get("month").upper())
        if month_num:
            conditions += " AND ss.month = %(month)s"
            values["month"] = month_num

    query = f"""
        SELECT 
            ss.employee,
            ss.employee_name,
            ss.fiscal_year,
            ss.month,
            ss.designation,
            ss.department,
            sd.salary_component,
            sd.amount,
            ss.name as salary_slip
        FROM `tabSalary Slip` ss
        INNER JOIN `tabSalary Detail` sd 
            ON ss.name = sd.parent
        WHERE sd.salary_component = 'SWS Loan Deduction'
          AND ss.docstatus = 1
          {conditions}
    """

    data = frappe.db.sql(query, values, as_dict=1)

    # Convert numeric month to abbreviation
    month_map = {
        1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY",
        6: "JUN", 7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT",
        11: "NOV", 12: "DEC"
    }

    for row in data:
        if isinstance(row.get("month"), int):
            row["month"] = month_map.get(row["month"], row["month"])
        elif isinstance(row.get("month"), str):
            try:
                # Handle date string format 'YYYY-MM-DD'
                row["month"] = month_map.get(int(row["month"].split("-")[1]), row["month"])
            except:
                pass

    return data
