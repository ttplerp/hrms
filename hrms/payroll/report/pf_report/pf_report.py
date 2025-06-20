# from __future__ import unicode_literals
# import frappe
# from frappe.utils import flt, cstr
# from frappe import msgprint, _


# def execute(filters=None):
#     if not filters:
#         filters = {}
#     columns = get_columns()
#     data = get_data(filters)
#     return columns, data

# def get_columns():
#     return [    
#         _("Salary Slip") + ":Link/Salary Slip:120",
#         _("Employee") + ":Link/Employee:80", 
#         _("Employee Name") + "::140", 
#         _("Designation") + ":Link/Designation:120",
#         _("Employment Type") + ":Data:120",
#         _("CID") + "::120",
#         _("PF Number") + "::120",
#         _("Basic Pay") + ":Float:120",
#         _("Employee PF") + ":Float:120", 
#         _("Employer PF") + ":Float:120", 
#         _("Company") + ":Link/Company:120", 
#         _("Month") + "::80",
#         _("Year") + "::80"
#     ]

# def get_data(filters):
#     conditions, filters = get_conditions(filters)
    
#     sql_query = """
#         SELECT 
#             t1.name as salary_slip,
#             t1.employee, 
#             t3.employee_name, 
#             t1.designation, 
#             t1.employment_type, 
#             t3.passport_number as cid, 
#             t3.pf_number,
#             (SELECT IFNULL(amount, 0) FROM `tabSalary Detail` 
#             WHERE parent = t1.name AND salary_component = 'Basic Pay' LIMIT 1) AS basic_pay,
#             (SELECT IFNULL(amount, 0) FROM `tabSalary Detail` 
#             WHERE parent = t1.name AND salary_component = 'PF' LIMIT 1) AS employee_pf,
#             IFNULL(t1.employer_pf, 0) AS employer_pf,
#             t1.company,
#             ELT(t1.month, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
#                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec') AS month,
#             t1.fiscal_year
#         FROM `tabSalary Slip` t1
#         JOIN `tabEmployee` t3 ON t3.name = t1.employee
#         WHERE t1.docstatus = 1
#         {conditions}
#         ORDER BY t1.employee, t1.fiscal_year, t1.month
#     """.format(conditions=conditions)

#     return frappe.db.sql(sql_query, filters, as_dict=1)

# def get_conditions(filters):
#     conditions = ""
#     if filters.get("fiscal_year"):
#         conditions += " AND t1.fiscal_year = %(fiscal_year)s"
#     if filters.get("month"):
#         month_list = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
#                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
#         if filters["month"] in month_list:
#             filters["month"] = month_list.index(filters["month"])
#             conditions += " AND t1.month = %(month)s"
#     if filters.get("employee"):
#         conditions += " AND t1.employee = %(employee)s"
#     if filters.get("employment_type"):
#         conditions += " AND t1.employment_type = %(employment_type)s"
#     if filters.get("company"):
#         conditions += " AND t1.company = %(company)s"
#     return conditions, filters



from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _


def execute(filters=None):
    if not filters:
        filters = {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [    
        _("Account Number") + "::120",
        _("Employee Name") + "::140", 
        _("Basic Pay") + ":Float:120",
        _("Employee PF") + ":Float:120", 
        _("Employer PF") + ":Float:120", 
        _("Total") + ":Float:120", 
       
    ]

def get_data(filters):
    conditions, filters = get_conditions(filters)
    
    sql_query = """
        SELECT 
            t3.employee_name, 
            t3.bank_ac_no as account_number,
            (SELECT IFNULL(amount, 0) FROM `tabSalary Detail` 
            WHERE parent = t1.name AND salary_component = 'Basic Pay') AS basic_pay,
            (SELECT IFNULL(amount, 0) FROM `tabSalary Detail` 
            WHERE parent = t1.name AND salary_component = 'PF') AS employee_pf,
            IFNULL(t1.employer_pf, 0) AS employer_pf,
            (SELECT IFNULL(amount, 0) FROM `tabSalary Detail` 
            WHERE parent = t1.name AND salary_component = 'PF') + IFNULL(t1.employer_pf, 0) AS total,
            t1.company,
            ELT(t1.month, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec') AS month,
            t1.fiscal_year
        FROM `tabSalary Slip` t1
        JOIN `tabEmployee` t3 ON t3.name = t1.employee
        WHERE t1.docstatus = 1 AND t3.employment_status != "Left"
        {conditions}
        ORDER BY t1.employee, t1.fiscal_year, t1.month
    """.format(conditions=conditions)

    return frappe.db.sql(sql_query, filters, as_dict=1)

def get_conditions(filters):
    conditions = ""
    if filters.get("fiscal_year"):
        conditions += " AND t1.fiscal_year = %(fiscal_year)s"
    if filters.get("month"):
        month_list = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        if filters["month"] in month_list:
            filters["month"] = month_list.index(filters["month"])
            conditions += " AND t1.month = %(month)s"
    if filters.get("employee"):
        conditions += " AND t1.employee = %(employee)s"
    if filters.get("employment_type"):
        conditions += " AND t1.employment_type = %(employment_type)s"
    if filters.get("company"):
        conditions += " AND t1.company = %(company)s"
    return conditions, filters