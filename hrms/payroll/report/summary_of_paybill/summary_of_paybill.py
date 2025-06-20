

# # Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# # For license information, please see license.txt

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

#     columns, earning_types, ded_types = get_columns(salary_structures)
#     ss_earning_map = get_ss_earning_map(salary_structures)
#     ss_ded_map = get_ss_ded_map(salary_structures)

#     # Group data by department only
#     department_data = {}

#     for ss in salary_structures:
#         dept = ss.department

#         if dept not in department_data:
#             department_data[dept] = {
#                 "earnings": {e: 0 for e in earning_types},
#                 "arrear_amount": 0,
#                 "leave_encashment_amount": 0,
#                 "deductions": {d: 0 for d in ded_types},
#             }

#         dept_entry = department_data[dept]

#         # Add earnings
#         for e in earning_types:
#             amount = flt(ss_earning_map.get(ss.name, {}).get(e))
#             dept_entry["earnings"][e] += amount

#         # Add special amounts
#         dept_entry["arrear_amount"] += flt(ss.arrear_amount)
#         dept_entry["leave_encashment_amount"] += flt(ss.leave_encashment_amount)

#         # Add deductions
#         for d in ded_types:
#             amount = flt(ss_ded_map.get(ss.name, {}).get(d))
#             dept_entry["deductions"][d] += amount

#     # Prepare final data rows
#     for department, dept_data in department_data.items():
#         gross_pay = sum(dept_data["earnings"].values()) + dept_data["arrear_amount"] + dept_data["leave_encashment_amount"]
#         total_ded = sum(dept_data["deductions"].values())
#         net_pay = gross_pay - total_ded

#         row = [department]

#         for e in earning_types:
#             row.append(dept_data["earnings"][e])

#         row += [dept_data["arrear_amount"], dept_data["leave_encashment_amount"], gross_pay]

#         for d in ded_types:
#             row.append(dept_data["deductions"][d])

#         row += [total_ded, net_pay]

#         data.append(row)

#     return columns, data


# def get_columns(salary_structures):
#     columns = [
#         _("Department") + ":Link/Department:180"
#     ]

#     earning_types = frappe.db.sql_list("""select salary_component from `tabSalary Detail`
#                     where amount != 0 and parent in (%s)
#                     and parentfield = 'earnings'
#                     group by salary_component
#                     order by count(*) desc""" %
#                                    (', '.join(['%s'] * len(salary_structures))),
#                                    tuple([d.name for d in salary_structures]))

#     ded_types = frappe.db.sql_list("""select salary_component from `tabSalary Detail`
#                     where amount != 0 and parent in (%s)
#                     and parentfield = 'deductions'
#                     group by salary_component
#                     order by count(*) desc""" %
#                                (', '.join(['%s'] * len(salary_structures))),
#                                tuple([d.name for d in salary_structures]))

#     columns += [(e + ":Currency:120") for e in earning_types]
#     columns += ["Arrear Amount:Currency:120", "Leave Encashment Amount:Currency:150", "Gross Pay:Currency:120"]
#     columns += [(d + ":Currency:120") for d in ded_types]
#     columns += ["Total Deduction:Currency:120", "Net Pay:Currency:120"]

#     return columns, earning_types, ded_types


# def get_salary_structures(filters):
#     conditions, filters = get_conditions(filters)
#     salary_structures = frappe.db.sql("""
#         select t1.*, t2.bank_name, t2.bank_ac_no as bank_account_no
#         from `tabSalary Structure` as t1, `tabEmployee` as t2
#         where t2.name = t1.employee
#         %s
#         order by t1.department
#     """ % conditions, filters, as_dict=1)

#     return salary_structures


# def get_conditions(filters):
#     conditions = ""
#     status = {
#         "All": "",
#         "Active": "Yes",
#         "Inactive": "No"
#     }.get(filters.get("status"), "")

#     if filters.get("department"):
#         conditions += " and t1.department = %(department)s"
#     if status:
#         conditions += " and t1.is_active = '{0}'".format(status)

#     return conditions, filters


# def get_ss_earning_map(salary_structures):
#     ss_earning_map = {}

#     ss_earnings = frappe.db.sql("""
#         select parent, salary_component, sum(ifnull(amount,0)) as amount 
#         from `tabSalary Detail`
#         where parent in (%s)
#         and parentfield = 'earnings'
#         and ifnull(to_date, CURDATE()) >= DATE_ADD(LAST_DAY(DATE_SUB(CURDATE(), interval 30 day)), interval 1 day)
#         group by parent, salary_component
#     """ % (', '.join(['%s'] * len(salary_structures))),
#         tuple([d.name for d in salary_structures]), as_dict=1)

#     for d in ss_earnings:
#         ss_earning_map.setdefault(d.parent, frappe._dict())[d.salary_component] = flt(d.amount)

#     return ss_earning_map


# def get_ss_ded_map(salary_structures):
#     ss_deductions = frappe.db.sql("""
#         select parent, salary_component, sum(ifnull(amount,0)) as amount 
#         from `tabSalary Detail`
#         where parent in (%s)
#         and parentfield = 'deductions'
#         and ifnull(to_date, CURDATE()) >= DATE_ADD(LAST_DAY(DATE_SUB(CURDATE(), interval 30 day)), interval 1 day)
#         group by parent, salary_component
#     """ % (', '.join(['%s'] * len(salary_structures))),
#         tuple([d.name for d in salary_structures]), as_dict=1)

#     ss_ded_map = {}
#     for d in ss_deductions:
#         ss_ded_map.setdefault(d.parent, frappe._dict())[d.salary_component] = flt(d.amount)

#     return ss_ded_map





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

    # Group data by department
    department_data = {}

    for ss in salary_structures:
        dept = ss.department

        if dept not in department_data:
            department_data[dept] = {
                "employee_count": 0,
                "earnings": {e: 0 for e in earning_types},
                "arrear_amount": 0,
                "leave_encashment_amount": 0,
                "deductions": {d: 0 for d in ded_types},
            }

        dept_entry = department_data[dept]
        dept_entry["employee_count"] += 1  # Count each employee in the department

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

        row = [department, dept_data["employee_count"]]  # Add employee count after department

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
        _("Department") + ":Link/Department:180",
        _("Total Employee") + ":Int:120"  # Add employee count column
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

    columns += [(e + ":Float:120") for e in earning_types]
    columns += ["Arrear Amount:Float:120", "Leave Encashment Amount:Float:150", "Gross Pay:Float:120"]
    columns += [(d + ":Float:120") for d in ded_types]
    columns += ["Total Deduction:Float:120", "Net Pay:Float:120"]

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