# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
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

    # Aggregate data per department
    department_map = {}

    for ss in salary_structures:
        dept = ss.department
        if dept not in department_map:
            department_map[dept] = {
                "department": dept,
                "earnings": {et: 0 for et in earning_types},
                "deductions": {dt: 0 for dt in ded_types},
                "arrear": 0,
                "leave_encashment": 0,
                "gross": 0,
                "total_deduction": 0,
                "net_pay": 0
            }

        ddata = department_map[dept]

        for e in earning_types:
            val = flt(ss_earning_map.get(ss.name, {}).get(e))
            ddata["earnings"][e] += val
            ddata["gross"] += val

        ddata["arrear"] += flt(ss.arrear_amount)
        ddata["leave_encashment"] += flt(ss.leave_encashment_amount)
        ddata["gross"] += flt(ss.arrear_amount) + flt(ss.leave_encashment_amount)

        for d in ded_types:
            val = flt(ss_ded_map.get(ss.name, {}).get(d))
            ddata["deductions"][d] += val
            ddata["total_deduction"] += val

        ddata["net_pay"] = ddata["gross"] - ddata["total_deduction"]

    # Prepare final output rows
    for dept, ddata in department_map.items():
        row = [ddata["department"]]
        row += [ddata["earnings"].get(e, 0) for e in earning_types]
        row += [ddata["arrear"], ddata["leave_encashment"], ddata["gross"]]
        row += [ddata["deductions"].get(d, 0) for d in ded_types]
        row += [ddata["total_deduction"], ddata["net_pay"]]
        data.append(row)

    return columns, data


def get_salary_structures(filters):
    conditions, filters = get_conditions(filters)
    return frappe.db.sql("""
        SELECT t1.*, t2.bank_name, t2.bank_ac_no as bank_account_no
        FROM `tabSalary Structure` t1
        INNER JOIN `tabEmployee` t2 ON t2.name = t1.employee
        WHERE 1=1 {0}
        ORDER BY t1.employee
    """.format(conditions), filters, as_dict=1)


def get_conditions(filters):
    conditions = ""
    if filters.get("department"):
        conditions += " AND t1.department = %(department)s"
    return conditions, filters


def get_columns(salary_structures):
    columns = [
        _("Department") + ":Link/Department:150",
    ]

    salary_structure_names = [d.name for d in salary_structures]

    earning_types = frappe.db.sql_list("""
        SELECT DISTINCT salary_component FROM `tabSalary Detail`
        WHERE amount != 0 AND parentfield = 'earnings' AND parent IN ({})
    """.format(', '.join(['%s'] * len(salary_structure_names))), tuple(salary_structure_names))

    ded_types = frappe.db.sql_list("""
        SELECT DISTINCT salary_component FROM `tabSalary Detail`
        WHERE amount != 0 AND parentfield = 'deductions' AND parent IN ({})
    """.format(', '.join(['%s'] * len(salary_structure_names))), tuple(salary_structure_names))

    columns += [(e + ":Currency:120") for e in earning_types]
    columns += ["Arrear Amount:Currency:130", "Leave Encashment Amount:Currency:130", "Gross Pay:Currency:120"]
    columns += [(d + ":Currency:120") for d in ded_types]
    columns += ["Total Deduction:Currency:130", "Net Pay:Currency:130"]

    return columns, earning_types, ded_types


def get_ss_earning_map(salary_structures):
    ss_earning_map = {}
    names = [d.name for d in salary_structures]

    ss_earnings = frappe.db.sql("""
        SELECT parent, salary_component, SUM(IFNULL(amount, 0)) AS amount
        FROM `tabSalary Detail`
        WHERE parent IN ({}) AND parentfield = 'earnings'
        GROUP BY parent, salary_component
    """.format(', '.join(['%s'] * len(names))), tuple(names), as_dict=1)

    for d in ss_earnings:
        ss_earning_map.setdefault(d.parent, {}).setdefault(d.salary_component, 0)
        ss_earning_map[d.parent][d.salary_component] = flt(d.amount)

    return ss_earning_map


def get_ss_ded_map(salary_structures):
    ss_ded_map = {}
    names = [d.name for d in salary_structures]

    ss_deductions = frappe.db.sql("""
        SELECT parent, salary_component, SUM(IFNULL(amount, 0)) AS amount
        FROM `tabSalary Detail`
        WHERE parent IN ({}) AND parentfield = 'deductions'
        GROUP BY parent, salary_component
    """.format(', '.join(['%s'] * len(names))), tuple(names), as_dict=1)

    for d in ss_deductions:
        ss_ded_map.setdefault(d.parent, {}).setdefault(d.salary_component, 0)
        ss_ded_map[d.parent][d.salary_component] = flt(d.amount)

    return ss_ded_map
