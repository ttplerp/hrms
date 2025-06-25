# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
# from frappe import _


# def execute(filters=None):
# 	if not filters:
# 		filters = {}
# 	columns, data = [], []
# 	data = get_data(filters)
# 	if not data:
# 		return columns, data
# 	columns = get_columns(data)
# 	return columns, data

# def get_columns(data):
# 	columns = [
# 		_("Employee") + ":Link/Employee:80", 
# 		_("Employee Name") + ":Data:140", 
# 		_("CID") + ":Data:120", 
# 		_("Designation") + ":Link/Designation:120",
# 		_("Loan Type") + ":Data:140", 
# 		_("Loan From") + ":Data:160", 
# 		_("Account No") + ":Data:140",  
# 		_("Deduction Amount") + ":Float:140", 
# 		_("Company") + ":Link/Company:120", 
# 		_("Cost Center") + ":Link/Cost Center:120", 
# 		_("Branch") + ":Link/Branch:120", 
# 		_("Department") + ":Link/Department:120",
# 		_("Division") + ":Link/Division:120", 
# 		_("Section") + ":Link/Section:120", 
# 		_("Year") + ":Data:80", 
# 		_("Month") + ":Data:80"
# 	]
# 	return columns

# def get_data(filters):
# 	conditions, filters = get_conditions(filters)

# 	sql = """
# 		SELECT 
# 			t1.employee, 
# 			t3.employee_name, 
# 			t3.passport_number, 
# 			t1.designation,
# 			t2.reference_type, 
# 			t2.institution_name, 
# 			t2.reference_number, 
# 			t2.amount, 
# 			t1.company, 
# 			t1.cost_center, 
# 			t1.branch, 
# 			t1.department, 
# 			t1.division, 
# 			t1.section,
# 			t1.fiscal_year, 
# 			CASE 
# 				WHEN t1.month = 1 THEN 'Jan'
# 				WHEN t1.month = 2 THEN 'Feb'
# 				WHEN t1.month = 3 THEN 'Mar'
# 				WHEN t1.month = 4 THEN 'Apr'
# 				WHEN t1.month = 5 THEN 'May'
# 				WHEN t1.month = 6 THEN 'Jun'
# 				WHEN t1.month = 7 THEN 'Jul'
# 				WHEN t1.month = 8 THEN 'Aug'
# 				WHEN t1.month = 9 THEN 'Sep'
# 				WHEN t1.month = 10 THEN 'Oct'
# 				WHEN t1.month = 11 THEN 'Nov'
# 				WHEN t1.month = 12 THEN 'Dec'
# 				ELSE ''
# 			END as month
# 		FROM `tabSalary Slip` t1
# 		JOIN `tabSalary Detail` t2 ON t2.parent = t1.name AND t2.parentfield = 'deductions'
# 		JOIN `tabEmployee` t3 ON t3.employee = t1.employee
# 		WHERE t1.docstatus = 1 
# 		AND EXISTS (
# 			SELECT 1 FROM `tabSalary Component` sc 
# 			WHERE sc.name = t2.salary_component
# 			AND sc.salary_component = 'Financial Institution Loan'
# 		)
# 		{conditions}
# 	""".format(conditions=conditions)

# 	return frappe.db.sql(sql, filters)


# def get_conditions(filters):
# 	conditions = ""
# 	if filters.get("month"):
# 		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
# 			"Dec"].index(filters["month"]) + 1
# 		filters["month"] = month
# 		conditions += " and t1.month = %(month)s"
	
# 	if filters.get("fiscal_year"): conditions += " and t1.fiscal_year = %(fiscal_year)s"
# 	if filters.get("company"): conditions += " and t1.company = %(company)s"
# 	if filters.get("employee"): conditions += " and t1.employee = %(employee)s"
# 	if filters.get("bank"): conditions += "and t2.institution_name = '{0}'".format(filters.bank)
# 	if filters.get("cost_center"): conditions += " and exists(select 1 from `tabCost Center` cc where t1.cost_center = cc.name and (cc.parent_cost_center = '{0}' or cc.name = '{0}'))".format(filters.cost_center)

# 	return conditions, filters

# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 80},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 140},
        {"label": _("CID"), "fieldname": "cid", "fieldtype": "Data", "width": 120},
        {"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 120},
        {"label": _("Loan Type"), "fieldname": "loan_type", "fieldtype": "Data", "width": 140},
        {"label": _("Loan From"), "fieldname": "loan_from", "fieldtype": "Data", "width": 160},
        {"label": _("Account No"), "fieldname": "account_no", "fieldtype": "Data", "width": 140},
        {"label": _("Deduction Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140},
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
        {"label": _("Cost Center"), "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 120},
        {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
        {"label": _("Division"), "fieldname": "division", "fieldtype": "Link", "options": "Division", "width": 120},
        {"label": _("Section"), "fieldname": "section", "fieldtype": "Link", "options": "Section", "width": 120},
        {"label": _("Year"), "fieldname": "year", "fieldtype": "Data", "width": 80},
        {"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 80}
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    data = frappe.db.sql("""
        SELECT 
            ss.employee, 
            emp.employee_name, 
            emp.passport_number as cid, 
            ss.designation,
            sd.reference_type as loan_type, 
            sd.institution_name as loan_from, 
            sd.reference_number as account_no, 
            sd.amount, 
            ss.company, 
            ss.cost_center, 
            ss.branch, 
            ss.department, 
            ss.division, 
            ss.section,
            ss.fiscal_year as year, 
            CASE 
                WHEN ss.month = 1 THEN 'Jan'
                WHEN ss.month = 2 THEN 'Feb'
                WHEN ss.month = 3 THEN 'Mar'
                WHEN ss.month = 4 THEN 'Apr'
                WHEN ss.month = 5 THEN 'May'
                WHEN ss.month = 6 THEN 'Jun'
                WHEN ss.month = 7 THEN 'Jul'
                WHEN ss.month = 8 THEN 'Aug'
                WHEN ss.month = 9 THEN 'Sep'
                WHEN ss.month = 10 THEN 'Oct'
                WHEN ss.month = 11 THEN 'Nov'
                WHEN ss.month = 12 THEN 'Dec'
                ELSE ''
            END as month
        FROM `tabSalary Slip` ss
        INNER JOIN `tabSalary Detail` sd ON sd.parent = ss.name AND sd.parentfield = 'deductions'
        INNER JOIN `tabEmployee` emp ON emp.name = ss.employee
        WHERE ss.docstatus = 1 
        AND sd.salary_component IN (
            SELECT name FROM `tabSalary Component` 
            WHERE salary_component LIKE '%%Financial Institution Loan%%' OR name LIKE '%%Financial Institution Loan%%'
        )
        {conditions}
        ORDER BY ss.employee, ss.fiscal_year, ss.month
    """.format(conditions=conditions), filters, as_dict=1)
    
    return data

def get_conditions(filters):
    conditions = ""
    
    if filters.get("month"):
        month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(filters["month"]) + 1
        filters["month"] = month
        conditions += " AND ss.month = %(month)s"
    
    if filters.get("fiscal_year"): 
        conditions += " AND ss.fiscal_year = %(fiscal_year)s"
    if filters.get("company"): 
        conditions += " AND ss.company = %(company)s"
    if filters.get("employee"): 
        conditions += " AND ss.employee = %(employee)s"
    if filters.get("bank"): 
        conditions += " AND sd.institution_name = %(bank)s"
    if filters.get("cost_center"): 
        conditions += """ AND EXISTS(
            SELECT 1 FROM `tabCost Center` cc 
            WHERE ss.cost_center = cc.name 
            AND (cc.parent_cost_center = %(cost_center)s OR cc.name = %(cost_center)s)
        """
    
    return conditions