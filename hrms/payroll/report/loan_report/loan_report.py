# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}
	columns, data = [], []
	data = get_data(filters)
	if not data:
		return columns, data
	columns = get_columns(data)
	return columns, data

def get_columns(data):
	columns = [
		_("Employee") + ":Link/Employee:80", 
		_("Employee Name") + ":Data:140", 
		_("CID") + ":Data:120", 
		_("Designation") + ":Link/Designation:120",
		_("Loan Type") + ":Data:140", 
		_("Loan From") + ":Data:160", 
		_("Account No") + ":Data:140",  
		_("Deduction Amount") + ":Currency:140", 
		_("Company") + ":Link/Company:120", 
		_("Cost Center") + ":Link/Cost Center:120", 
		_("Branch") + ":Link/Branch:120", 
		_("Department") + ":Link/Department:120",
		_("Division") + ":Link/Division:120", 
		_("Section") + ":Link/Section:120", 
		_("Year") + ":Data:80", 
		_("Month") + ":Data:80"
	]
	return columns

def get_data(filters):
	conditions, filters = get_conditions(filters)

	sql = """
		SELECT 
			t1.employee, 
			t3.employee_name, 
			t3.passport_number, 
			t1.designation,
			t2.reference_type, 
			t2.institution_name, 
			t2.reference_number, 
			t2.amount, 
			t1.company, 
			t1.cost_center, 
			t1.branch, 
			t1.department, 
			t1.division, 
			t1.section,
			t1.fiscal_year, 
			CASE 
				WHEN t1.month = 1 THEN 'Jan'
				WHEN t1.month = 2 THEN 'Feb'
				WHEN t1.month = 3 THEN 'Mar'
				WHEN t1.month = 4 THEN 'Apr'
				WHEN t1.month = 5 THEN 'May'
				WHEN t1.month = 6 THEN 'Jun'
				WHEN t1.month = 7 THEN 'Jul'
				WHEN t1.month = 8 THEN 'Aug'
				WHEN t1.month = 9 THEN 'Sep'
				WHEN t1.month = 10 THEN 'Oct'
				WHEN t1.month = 11 THEN 'Nov'
				WHEN t1.month = 12 THEN 'Dec'
				ELSE ''
			END as month
		FROM `tabSalary Slip` t1
		JOIN `tabSalary Detail` t2 ON t2.parent = t1.name AND t2.parentfield = 'deductions'
		JOIN `tabEmployee` t3 ON t3.employee = t1.employee
		WHERE t1.docstatus = 1
		AND t2.institution_name != 'RICBL'
		AND EXISTS (
			SELECT 1 FROM `tabSalary Component` sc WHERE sc.name = t2.salary_component
		)
		{conditions}
	""".format(conditions=conditions)

	return frappe.db.sql(sql, filters)


def get_conditions(filters):
	conditions = ""
	if filters.get("month"):
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
			"Dec"].index(filters["month"]) + 1
		filters["month"] = month
		conditions += " and t1.month = %(month)s"
	
	if filters.get("fiscal_year"): conditions += " and t1.fiscal_year = %(fiscal_year)s"
	if filters.get("company"): conditions += " and t1.company = %(company)s"
	if filters.get("employee"): conditions += " and t1.employee = %(employee)s"
	if filters.get("bank"): conditions += "and t2.institution_name = '{0}'".format(filters.bank)
	if filters.get("cost_center"): conditions += " and exists(select 1 from `tabCost Center` cc where t1.cost_center = cc.name and (cc.parent_cost_center = '{0}' or cc.name = '{0}'))".format(filters.cost_center)

	return conditions, filters
