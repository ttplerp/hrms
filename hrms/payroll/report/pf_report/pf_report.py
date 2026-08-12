# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}
	columns, data = [], []
	data = get_data(filters)
	if not data:
		return get_columns(), []

	columns = get_columns()
	return columns, data


def get_columns():
	columns = [
		_("Employee") + ":Link/Employee:80", 
		_("Employee Name") + "::140", 
		_("Designation") + ":Link/Designation:120",
		_("Employment Type") + ":Data:120",
		_("CID") + "::120",
		_("PF Number") + "::120",
		_("Basic Pay") + ":Currency:120",
		_("Employee PF") + ":Currency:120", 
		_("Employer PF") + ":Currency:120", 
		_("Total PF") + ":Currency:120",
		_("Company") + ":Link/Company:120", 
		_("Cost Center") + ":Link/Cost Center:120", 
		_("Branch") + ":Link/Branch:120", 
		_("Department") + ":Link/Department:120",
		_("Division") + ":Link/Division:120", 
		_("Year") + "::80", 
		_("Month") + "::80"
	]
	return columns


def get_data(filters):
	conditions, filters = get_conditions(filters)

	# Fetch Salary Slip + Basic Pay + PF rates from Employee Qualification
	# Also check eligible_for_pf from Salary Structure
	data = frappe.db.sql("""
		select 
			t1.employee, 
			t3.employee_name, 
			t1.designation, 
			t1.employment_type, 
			t3.passport_number, 
			t3.pf_number,
			sum(case when t2.salary_component = 'Basic Pay' then ifnull(t2.amount,0) else 0 end) as basicpay,
			eq.employee_pf as employee_pf_rate,
			eq.employer_pf as employer_pf_rate,
			t1.company, t1.branch, t1.cost_center, t1.department, t1.division,
			t1.fiscal_year, t1.month,
			ss.eligible_for_pf as eligible_for_pf
		from `tabSalary Slip` t1
		join `tabSalary Detail` t2 on t2.parent = t1.name
		join `tabEmployee` t3 on t3.employee = t1.employee
		left join `tabEmployee Qualification` eq on eq.name = t3.employee_qualification
		left join `tabSalary Structure` ss on ss.name = t1.salary_structure
		where t1.docstatus = 1 %s
		and t2.salary_component = 'Basic Pay'
		group by t1.employee, t3.employee_name, t1.designation,
				 t1.company, t1.branch, t1.cost_center, t1.department, t1.division,
				 t1.fiscal_year, t1.month, eq.employee_pf, eq.employer_pf, ss.eligible_for_pf
	""" % conditions, filters, as_dict=True)

	result = []
	for row in data:
		basicpay = row.basicpay or 0
		
		# Check if eligible for PF, if not set all PF amounts to 0
		if not row.eligible_for_pf:
			employee_pf = 0
			employer_pf = 0
			total = 0
		else:
			employee_pf = basicpay * (row.employee_pf_rate or 0) / 100
			employer_pf = basicpay * (row.employer_pf_rate or 0) / 100
			total = employee_pf + employer_pf

		result.append([
			row.employee,
			row.employee_name,
			row.designation,
			row.employment_type,
			row.passport_number,
			row.pf_number,
			basicpay,
			employee_pf,
			employer_pf,
			total,
			row.company,
			row.cost_center,
			row.branch,
			row.department,
			row.division,
			row.fiscal_year,
			row.month
		])

	return result


def get_conditions(filters):
	conditions = ""
	if filters.get("fiscal_year"): 
		conditions += " and t1.fiscal_year = %(fiscal_year)s"
	if filters.get("month"):
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(filters["month"]) + 1
		filters["month"] = month
		conditions += " and t1.month = %(month)s"
	if filters.get("employee"): 
		conditions += " and t1.employee = %(employee)s"
	if filters.get("employment_type"): 
		conditions += " and t1.employment_type = %(employment_type)s"
	if filters.get("cost_center"): 
		conditions += """ and exists(
			select 1 from `tabCost Center` cc 
			where t1.cost_center = cc.name 
			  and (cc.parent_cost_center = '{0}' or cc.name = '{0}')
		)""".format(filters.cost_center)
	if filters.get("company"): 
		conditions += " and t1.company = %(company)s"
	return conditions, filters