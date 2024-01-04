# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
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
		_("Employee") + ":Link/Employee:120", 
		_("Employee Name") + "::150", 
		_("Branch") + ":Link/Branch:200",
		_("Lumpsum Increment") + ":Currency:150", 
		_("Arrear Ltc") + ":Currency:120", 
		_("Arrear HC") + ":Currency:120",
		_("Arrear Salary Tax") + ":Currency:150", 
		_("Year") + "::80", 
		_("Month") + "::80"
	]
	return columns

def get_data(filters):
	conditions, filters = get_conditions(filters)
	data = frappe.db.sql("""
		select 
			t2.employee,
			t2.employee_name,
			t2.branch,
			t2.fixed_allowance,
			t2.arrear_ltc,
			t2.arrear_hc,
			t2.arrear_salary_tax,
			t1.fiscal_year,
			t1.from_month
		from `tabSalary Arrear Payment` t1
		INNER JOIN
			`tabSalary Arrear Payment Item` t2
		ON
			t1.name=t2.parent
		where t1.docstatus = 1 %s
		""" % conditions, filters)
	return data

def get_conditions(filters):
	conditions = ""
	if filters.get("month"):
		conditions += " and t1.from_month = %(month)s"
	if filters.get("fiscal_year"): conditions += " and t1.fiscal_year = %(fiscal_year)s"
	# if filters.get("company"): conditions += " and t1.company = %(company)s"
	if filters.get("employee"): conditions += " and t2.employee = %(employee)s"

	return conditions, filters
