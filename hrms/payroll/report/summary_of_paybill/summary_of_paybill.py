# from __future__ import unicode_literals
# import frappe
# from frappe import _
# from frappe.utils import flt


# def execute(filters=None):
#     if not filters:
#         filters = {}

#     data = []
#     columns = []
#     salary_structures = get_salary_structures(filters)
#     if not salary_structures:
#         return columns, data

#     columns, earning_types, ded_types = get_columns()
#     ss_earning_map = get_ss_earning_map(salary_structures)
#     ss_ded_map = get_ss_ded_map(salary_structures)

#     # Aggregate data per department
#     department_map = {}

#     for ss in salary_structures:
#         # Apply status filter if specified
#         if filters.get("status") and filters.get("status") != "All":
#             if filters.get("status") == "Active" and ss.is_active != "Yes":
#                 continue
#             if filters.get("status") == "Inactive" and ss.is_active == "Yes":
#                 continue
                
#         dept = ss.department
#         if dept not in department_map:
#             department_map[dept] = {
#                 "department": dept,
#                 "Basic Pay": 0,
#                 "HRA": 0,
#                 "DA": 0,
#                 "Special Allowance": 0,
#                 "Other Earnings": 0,
#                 "arrear": 0,
#                 "leave_encashment": 0,
#                 "gross": 0,
#                 "PF": 0,
#                 "Professional Tax": 0,
#                 "TDS": 0,
#                 "Other Deductions": 0,
#                 "total_deduction": 0,
#                 "net_pay": 0
#             }

#         ddata = department_map[dept]

#         # Process earnings
#         for etype, amount in ss_earning_map.get(ss.name, {}).items():
#             amount = flt(amount)
#             if "Basic" in etype:
#                 ddata["Basic Pay"] += amount
#             elif "HRA" in etype or "House Rent" in etype:
#                 ddata["HRA"] += amount
#             elif "DA" in etype or "Dearness" in etype:
#                 ddata["DA"] += amount
#             elif "Special Allowance" in etype:
#                 ddata["Special Allowance"] += amount
#             else:
#                 ddata["Other Earnings"] += amount
#             ddata["gross"] += amount

#         # Process arrear and leave encashment
#         ddata["arrear"] += flt(ss.arrear_amount)
#         ddata["leave_encashment"] += flt(ss.leave_encashment_amount)
#         ddata["gross"] += flt(ss.arrear_amount) + flt(ss.leave_encashment_amount)

#         # Process deductions
#         for dtype, amount in ss_ded_map.get(ss.name, {}).items():
#             amount = flt(amount)
#             if "PF" in dtype or "Provident" in dtype:
#                 ddata["PF"] += amount
#             elif "Professional Tax" in dtype or "PT" in dtype:
#                 ddata["Professional Tax"] += amount
#             elif "TDS" in dtype or "Tax" in dtype:
#                 ddata["TDS"] += amount
#             else:
#                 ddata["Other Deductions"] += amount
#             ddata["total_deduction"] += amount

#         ddata["net_pay"] = ddata["gross"] - ddata["total_deduction"]

#     # Prepare final output rows
#     for dept, ddata in department_map.items():
#         row = [
#             ddata["department"],
#             ddata["Basic Pay"],
#             ddata["HRA"],
#             ddata["DA"],
#             ddata["Special Allowance"],
#             ddata["Other Earnings"],
#             ddata["arrear"],
#             ddata["leave_encashment"],
#             ddata["gross"],
#             ddata["PF"],
#             ddata["Professional Tax"],
#             ddata["TDS"],
#             ddata["Other Deductions"],
#             ddata["total_deduction"],
#             ddata["net_pay"]
#         ]
#         data.append(row)

#     return columns, data


# def get_salary_structures(filters):
#     conditions, filters = get_conditions(filters)
#     return frappe.db.sql("""
#         SELECT t1.*, t2.bank_name, t2.bank_ac_no as bank_account_no
#         FROM `tabSalary Structure` t1
#         INNER JOIN `tabEmployee` t2 ON t2.name = t1.employee
#         WHERE 1=1 {0}
#         ORDER BY t1.employee
#     """.format(conditions), filters, as_dict=1)


# def get_conditions(filters):
#     conditions = ""
#     if filters.get("department"):
#         conditions += " AND t1.department = %(department)s"
#     if filters.get("company"):
#         conditions += " AND t1.company = %(company)s"
#     if filters.get("from_date"):
#         conditions += " AND t1.from_date >= %(from_date)s"
#     if filters.get("to_date"):
#         conditions += " AND t1.to_date <= %(to_date)s"
#     return conditions, filters


# def get_columns():
#     columns = [
#         {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
#         {"label": _("Basic Pay"), "fieldname": "Basic Pay", "fieldtype": "Float", "width": 120},
#         {"label": _("HRA"), "fieldname": "HRA", "fieldtype": "Float", "width": 120},
#         {"label": _("DA"), "fieldname": "DA", "fieldtype": "Float", "width": 120},
#         {"label": _("Special Allowance"), "fieldname": "Special Allowance", "fieldtype": "Float", "width": 140},
#         {"label": _("Other Earnings"), "fieldname": "Other Earnings", "fieldtype": "Float", "width": 140},
#         {"label": _("Arrear Amount"), "fieldname": "arrear", "fieldtype": "Float", "width": 130},
#         {"label": _("Leave Encashment"), "fieldname": "leave_encashment", "fieldtype": "Float", "width": 150},
#         {"label": _("Gross Pay"), "fieldname": "gross", "fieldtype": "Float", "width": 120},
#         {"label": _("PF"), "fieldname": "PF", "fieldtype": "Float", "width": 120},
#         {"label": _("Professional Tax"), "fieldname": "Professional Tax", "fieldtype": "Float", "width": 150},
#         {"label": _("TDS"), "fieldname": "TDS", "fieldtype": "Float", "width": 120},
#         {"label": _("Other Deductions"), "fieldname": "Other Deductions", "fieldtype": "Float", "width": 150},
#         {"label": _("Total Deduction"), "fieldname": "total_deduction", "fieldtype": "Float", "width": 130},
#         {"label": _("Net Pay"), "fieldname": "net_pay", "fieldtype": "Float", "width": 130}
#     ]
    
#     earning_types = ["Basic Pay", "HRA", "DA", "Special Allowance", "Other Earnings"]
#     ded_types = ["PF", "Professional Tax", "TDS", "Other Deductions"]
    
#     return columns, earning_types, ded_types


# def get_ss_earning_map(salary_structures):
#     ss_earning_map = {}
#     names = [d.name for d in salary_structures]

#     ss_earnings = frappe.db.sql("""
#         SELECT parent, salary_component, SUM(IFNULL(amount, 0)) AS amount
#         FROM `tabSalary Detail`
#         WHERE parent IN ({}) AND parentfield = 'earnings'
#         GROUP BY parent, salary_component
#     """.format(', '.join(['%s'] * len(names))), tuple(names), as_dict=1)

#     for d in ss_earnings:
#         ss_earning_map.setdefault(d.parent, {}).setdefault(d.salary_component, 0)
#         ss_earning_map[d.parent][d.salary_component] = flt(d.amount)

#     return ss_earning_map


# def get_ss_ded_map(salary_structures):
#     ss_ded_map = {}
#     names = [d.name for d in salary_structures]

#     ss_deductions = frappe.db.sql("""
#         SELECT parent, salary_component, SUM(IFNULL(amount, 0)) AS amount
#         FROM `tabSalary Detail`
#         WHERE parent IN ({}) AND parentfield = 'deductions'
#         GROUP BY parent, salary_component
#     """.format(', '.join(['%s'] * len(names))), tuple(names), as_dict=1)

#     for d in ss_deductions:
#         ss_ded_map.setdefault(d.parent, {}).setdefault(d.salary_component, 0)
#         ss_ded_map[d.parent][d.salary_component] = flt(d.amount)

#     return ss_ded_map



# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    if not filters:
        filters = {}

    data = []
    columns = []
    salary_structures = get_salary_structures(filters)
    if not salary_structures:
        return columns, data

    columns, earning_types, ded_types = get_columns(salary_structures)
    ss_earning_map = get_ss_earning_map(salary_structures)
    ss_ded_map = get_ss_ded_map(salary_structures)

    # Group data by department only
    department_data = {}

    for ss in salary_structures:
        dept = ss.department

        if dept not in department_data:
            department_data[dept] = {
                "earnings": {e: 0 for e in earning_types},
                "arrear_amount": 0,
                "leave_encashment_amount": 0,
                "deductions": {d: 0 for d in ded_types},
            }

        dept_entry = department_data[dept]

        # Add earnings
        for e in earning_types:
            amount = flt(ss_earning_map.get(ss.name, {}).get(e))
            dept_entry["earnings"][e] += amount

        # Add special amounts
        dept_entry["arrear_amount"] += flt(ss.arrear_amount)
        dept_entry["leave_encashment_amount"] += flt(ss.leave_encashment_amount)

        # Add deductions
        for d in ded_types:
            amount = flt(ss_ded_map.get(ss.name, {}).get(d))
            dept_entry["deductions"][d] += amount

    # Prepare final data rows
    for department, dept_data in department_data.items():
        gross_pay = sum(dept_data["earnings"].values()) + dept_data["arrear_amount"] + dept_data["leave_encashment_amount"]
        total_ded = sum(dept_data["deductions"].values())
        net_pay = gross_pay - total_ded

        row = [department]

        for e in earning_types:
            row.append(dept_data["earnings"][e])

        row += [dept_data["arrear_amount"], dept_data["leave_encashment_amount"], gross_pay]

        for d in ded_types:
            row.append(dept_data["deductions"][d])

        row += [total_ded, net_pay]

        data.append(row)

    return columns, data


def get_columns(salary_structures):
    columns = [
        _("Department") + ":Link/Department:180"
    ]

    earning_types = frappe.db.sql_list("""select salary_component from `tabSalary Detail`
                    where amount != 0 and parent in (%s)
                    and parentfield = 'earnings'
                    group by salary_component
                    order by count(*) desc""" %
                                   (', '.join(['%s'] * len(salary_structures))),
                                   tuple([d.name for d in salary_structures]))

    ded_types = frappe.db.sql_list("""select salary_component from `tabSalary Detail`
                    where amount != 0 and parent in (%s)
                    and parentfield = 'deductions'
                    group by salary_component
                    order by count(*) desc""" %
                               (', '.join(['%s'] * len(salary_structures))),
                               tuple([d.name for d in salary_structures]))

    columns += [(e + ":Currency:120") for e in earning_types]
    columns += ["Arrear Amount:Currency:120", "Leave Encashment Amount:Currency:150", "Gross Pay:Currency:120"]
    columns += [(d + ":Currency:120") for d in ded_types]
    columns += ["Total Deduction:Currency:120", "Net Pay:Currency:120"]

    return columns, earning_types, ded_types


def get_salary_structures(filters):
    conditions, filters = get_conditions(filters)
    salary_structures = frappe.db.sql("""
        select t1.*, t2.bank_name, t2.bank_ac_no as bank_account_no
        from `tabSalary Structure` as t1, `tabEmployee` as t2
        where t2.name = t1.employee
        %s
        order by t1.department
    """ % conditions, filters, as_dict=1)

    return salary_structures


def get_conditions(filters):
    conditions = ""
    status = {
        "All": "",
        "Active": "Yes",
        "Inactive": "No"
    }.get(filters.get("status"), "")

    if filters.get("department"):
        conditions += " and t1.department = %(department)s"
    if status:
        conditions += " and t1.is_active = '{0}'".format(status)

    return conditions, filters


def get_ss_earning_map(salary_structures):
    ss_earning_map = {}

    ss_earnings = frappe.db.sql("""
        select parent, salary_component, sum(ifnull(amount,0)) as amount 
        from `tabSalary Detail`
        where parent in (%s)
        and parentfield = 'earnings'
        and ifnull(to_date, CURDATE()) >= DATE_ADD(LAST_DAY(DATE_SUB(CURDATE(), interval 30 day)), interval 1 day)
        group by parent, salary_component
    """ % (', '.join(['%s'] * len(salary_structures))),
        tuple([d.name for d in salary_structures]), as_dict=1)

    for d in ss_earnings:
        ss_earning_map.setdefault(d.parent, frappe._dict())[d.salary_component] = flt(d.amount)

    return ss_earning_map


def get_ss_ded_map(salary_structures):
    ss_deductions = frappe.db.sql("""
        select parent, salary_component, sum(ifnull(amount,0)) as amount 
        from `tabSalary Detail`
        where parent in (%s)
        and parentfield = 'deductions'
        and ifnull(to_date, CURDATE()) >= DATE_ADD(LAST_DAY(DATE_SUB(CURDATE(), interval 30 day)), interval 1 day)
        group by parent, salary_component
    """ % (', '.join(['%s'] * len(salary_structures))),
        tuple([d.name for d in salary_structures]), as_dict=1)

    ss_ded_map = {}
    for d in ss_deductions:
        ss_ded_map.setdefault(d.parent, frappe._dict())[d.salary_component] = flt(d.amount)

    return ss_ded_map
