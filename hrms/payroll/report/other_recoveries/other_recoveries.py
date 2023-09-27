# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}
	data = get_data(filters)
	columns = get_columns(data)

	return columns, data

def get_columns(data):
	columns = [
		("Employee") + ":Link/Employee:100",
		("Employee Name") + "::160",
		("Designation") + ":Link/Designation:150",
		("Branch") + ":Link/Branch:120",
		("Amount") + ":Currency:100",
	]

	return columns

def get_data(filters):
	conditions, filters = get_conditions(filters)
	data = frappe.db.sql(""" SELECT ss.employee, ss.employee_name,  ss.designation, ss.branch, sd.amount
		FROM `tabSalary Slip` AS ss , `tabSalary Detail` AS sd
		WHERE ss.name= sd.parent
		AND sd.salary_component ='Other Recoveries' {0}""".format(conditions))

	return data

def get_conditions(filters):
	conditions = ""
	if filters.get("month"):
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov","Dec"].index(filters.get("month")) + 1
	filters["month"] = month
	conditions += " and ss.month = {0}".format(month)
	#frappe.msgprint(conditions)

	if filters.get("fiscal_year"): conditions += " and ss.fiscal_year = '{0}'".format(filters.fiscal_year)
	if filters.get("company"): conditions += " and ss.company = '{0}'".format(filters.company)
	if filters.get("employee"): conditions += " and ss.employee = '{0}'".format(filters.employee)
	if filters.get("branch"): conditions += " and ss.branch = '{0}'".format(filters.branch)
	#frappe.msgprint("{0}".format(conditions))
	return conditions, filters
