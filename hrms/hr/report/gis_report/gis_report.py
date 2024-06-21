# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
1.0		  SSK		                   03/08/2016         Taking care of Duplication of columns
--------------------------------------------------------------------------------------------------------------------------
'''

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _

def execute(filters=None):
	if not filters: 
		filters = {}
	data    = []
	columns = []
		
	data = get_data(filters)
	if not data:
				return columns, data
		
	columns = get_columns(data)

	return columns, data

def get_columns(data):
	columns = [
		_("Employee") + ":Link/Employee:100",
		_("Employee Name") + "::140",
		_("Designation") + ":Link/Designation:120",
		_("CID") + "::110",
		_("Date Of Birth") + "::100",
		_("Date Of Joining") + "::100",
		_("Group") + "::100",
		_("Grade") + "::60",
		_("GIS Number") + "::100",
		_("Policy Number") + "::100",
		_("Basic Pay") + ":Currency:120",
		_("GIS Contribution") + ":Currency:120",
		_("Company") + ":Link/Company:120",
		_("Branch") + ":Link/Branch:120",
		_("Cost Center") + ":Link/Cost Center:120",
		_("Department") + ":Link/Department:120",
		_("Division") + ":Data:120",
		_("Section") + ":Data:120",
		_("Year") + "::80",
		_("Month") + "::80",
		_("Pay Roll Entry ID") + ":Link/Payroll Entry:100",

	]

	return columns

def get_data(filters):
	conditions, filters = get_conditions(filters)
	# data = frappe.db.sql("""select 
	# 			t1.employee as n, t3.employee_name, t1.designation, t3.passport_number, 
	# 			t3.date_of_birth, t3.date_of_joining, t3.employee_group, t1.employee_subgroup, t1.gis_number, t1.gis_policy_number,
	# 			sum(case when t2.salary_component = 'Basic Pay' then ifnull(t2.amount,0) else 0 end) as basicpay,
	# 			sum(case when t2.salary_component = 'GIS' then ifnull(t2.amount,0) else 0 end) as gisamount,
	# 						t1.company, t1.branch, t1.cost_center, t1.department, t1.division, t1.section,t1.fiscal_year, t1.month
	# 					from `tabSalary Slip` t1, `tabSalary Detail` t2, `tabEmployee` t3, `tabSalary Slip Item` t4, `tabSalary Structure` t5
	# 					where t1.docstatus = 1 %s
	# 					and t3.employee = t1.employee
	# 					and t2.parent = t1.name
	# 					and t4.parent = t1.name
	# 					and t4.salary_structure = t5.name
	# 					and t2.salary_component in ('Basic Pay','GIS')
	# 					group by t1.employee, t3.employee_name, t1.designation, t3.passport_number,  t3.gis_number, 
	# 			t1.company, t1.branch, t1.department, t1.division, t1.section, t1.fiscal_year, t1.month
	# 			""" % conditions, filters)
	# data = frappe.db.sql("""select 
	# 			t1.employee as n, t3.employee_name, t1.designation, t3.passport_number, 
	# 			t3.date_of_birth, t3.date_of_joining, t3.employee_group, t1.employee_subgroup, t1.gis_number, t1.gis_policy_number,
	# 			(select sum(t6.amount) from `tabSalary Structure` t5, `tabSalary Slip Item` t4, `tabSalary Detail` t6 where t4.parent = t1.name and t4.salary_structure = t5.name and t6.parent = t5.name and t6.salary_component = 'Basic Pay') as basicpay,
	# 			sum(case when t2.salary_component = 'GIS' then ifnull(t2.amount,0) else 0 end) as gisamount,
	# 						t1.company, t1.branch, t1.cost_center, t1.department, t1.division, t1.section,t1.fiscal_year, t1.month
	# 					from `tabSalary Slip` t1, `tabSalary Detail` t2, `tabEmployee` t3
	# 					where t1.docstatus = 1 %s
	# 					and t3.employee = t1.employee
	# 					and t2.parent = t1.name
	# 					and t2.salary_component in ('GIS')
	# 					group by t1.employee, t3.employee_name, t1.designation, t3.passport_number,  t3.gis_number, 
	# 			t1.company, t1.branch, t1.department, t1.division, t1.section, t1.fiscal_year, t1.month
	# 			""" % conditions, filters)
	# return data




	data = frappe.db.sql("""
		SELECT 
			t1.employee AS n, 
			t3.employee_name, 
			t1.designation, 
			t3.passport_number, 
			t3.date_of_birth, 
			t3.date_of_joining, 
			t3.employee_group, 
			t1.employee_subgroup, 
			t1.gis_number, 
			t1.gis_policy_number,
			(SELECT SUM(t6.amount) 
			FROM `tabSalary Structure` t5, 
				`tabSalary Slip Item` t4, 
				`tabSalary Detail` t6 
			WHERE t4.parent = t1.name 
			AND t4.salary_structure = t5.name 
			AND t6.parent = t5.name 
			AND t6.salary_component = 'Basic Pay') AS basicpay,
			SUM(CASE 
				WHEN t2.salary_component = 'GIS' 
				THEN IFNULL(t2.amount, 0) 
				ELSE 0 
				END) AS gisamount,
			t1.company, 
			t1.branch, 
			t1.cost_center, 
			t1.department, 
			t1.division, 
			t1.section,
			t1.fiscal_year, 
			t1.month,
			t1.payroll_entry AS payroll_entry_id  -- Added payroll entry ID
		FROM 
			`tabSalary Slip` t1
		JOIN 
			`tabSalary Detail` t2 ON t2.parent = t1.name
		JOIN 
			`tabEmployee` t3 ON t3.employee = t1.employee
		LEFT JOIN 
			`tabPayroll Entry` t7 ON t7.name = t1.payroll_entry  -- Join with Payroll Entry table
		WHERE 
			t1.docstatus = 1 %s
			AND t2.salary_component IN ('GIS')
		GROUP BY 
			t1.employee, 
			t3.employee_name, 
			t1.designation, 
			t3.passport_number,  
			t3.gis_number, 
			t1.company, 
			t1.branch, 
			t1.department, 
			t1.division, 
			t1.section, 
			t1.fiscal_year, 
			t1.month,
			t1.payroll_entry
    """ % conditions, filters)
	return data


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
	if filters.get("cost_center"): conditions += " and exists(select 1 from `tabCost Center` cc where t1.cost_center = cc.name and (cc.parent_cost_center = '{0}' or cc.name = '{0}'))".format(filters.cost_center)

	return conditions, filters
