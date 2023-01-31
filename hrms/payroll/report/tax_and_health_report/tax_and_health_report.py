# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _


def execute(filters=None):
	if not filters:
		filters = {}
	columns, data = [], []
	data = get_data(filters)
	if not data:
		return columns, data
	columns =get_columns(data)
	return columns, data

def get_columns(data):
	columns = [
		_("Employee") + ":Link/Employee:80", 
		_("Employee Name") + "::140", 
		_("Designation") + ":Link/Designation:120",
		_("CID") + "::120", 
		_("TPN#") + "::80",
		_("Basic Salary") + ":Currency:120", 
		_("Allowances") + ":Currency:120", 
		_("Arrears") + ":Currency:120",
		_("Gross Salary(A)") + ":Currency:120", 
		_("PF Amount(B)") + ":Currency:120", 
		_("GIS Amount(C)") + ":Currency:120",
		_("Net Salary(A-(B+C))") + ":Currency:140", 
		_("Salary Tax(X)") + ":Currency:120", 
		_("Health Contr(Y)") + ":Currency:120",
		_("Total(X+Y)") + ":Currency:120", 
		_("Company") + ":Link/Company:120", 
		_("Cost Center") + ":Link/Cost Center:120",
		_("Branch") + ":Link/Branch:120", 
		_("Department") + ":Link/Department:120",
		_("Division") + ":Link/Division:120", 
		_("Section") + ":Link/Section:120", 
		_("Year") + "::80", 
		_("Month") + "::80"
	]
	return columns

def get_data(filters):
	conditions, filters = get_conditions(filters)
	data = frappe.db.sql("""
		select t1.employee, t3.employee_name, t1.designation, t3.passport_number, t3.tpn_number,
			sum(case when t2.salary_component = 'Basic Pay' then ifnull(t2.amount,0) else 0 end) as basicpay,
			sum(case when t2.parentfield = 'earnings'
				 then (case when t2.salary_component = 'Basic Pay' then 0
					    when t2.salary_component = 'Salary  Arrears' then 0
				       else ifnull(t2.amount,0) end)
				 else 0 end) as allowances,
			sum(case when t2.salary_component = 'Salary  Arrears' then ifnull(t2.amount,0) else 0 end) as arrears,
			sum(case when t2.parentfield = 'earnings' then ifnull(t2.amount,0) else 0 end) as grosspay,
			sum(case when t2.salary_component = 'PF' then ifnull(t2.amount,0) else 0 end) as pfamount,
			sum(case when t2.salary_component = 'GIS' then ifnull(t2.amount,0) else 0 end) as gisamount,
			sum(
			   (case when t2.parentfield = 'earnings' then ifnull(t2.amount,0) else 0 end)
			   - (case when t2.salary_component = 'PF' then ifnull(t2.amount,0) else 0 end)
			   - (case when t2.salary_component = 'GIS' then ifnull(t2.amount,0) else 0 end)
			) as netpay,
			sum(case when t2.salary_component = 'Salary Tax' then ifnull(t2.amount,0) else 0 end) as salarytax,
			sum(case when t2.salary_component = 'Health Contribution' then ifnull(t2.amount,0) else 0 end) as healthcont,
			sum(
			   (case when t2.salary_component = 'Salary Tax' then ifnull(t2.amount,0) else 0 end)
			   + (case when t2.salary_component = 'Health Contribution' then ifnull(t2.amount,0) else 0 end)
			) as total,
			t1.company, t1.cost_center, t1.branch, t1.department, t1.division, t1.section,
			t1.fiscal_year, t1.month
		from `tabSalary Slip` t1, `tabSalary Detail` t2, `tabEmployee` t3
		where t1.docstatus = 1 %s
		and t3.employee = t1.employee
		and t2.parent = t1.name
		group by t1.employee, t3.employee_name, t1.designation, t3.passport_number,
			t3.tpn_number, t1.company, t1.branch, t1.department, t1.division, t1.section,
			t1.fiscal_year, t1.month
		""" % conditions, filters)

	'''
	if not data:
		msgprint(_("No Data Found for month: ") + cstr(filters.get("month")) + 
			_(" and year: ") + cstr(filters.get("fiscal_year")), raise_exception=1)
	'''
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
