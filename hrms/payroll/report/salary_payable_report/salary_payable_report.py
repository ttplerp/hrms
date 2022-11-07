# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _

def execute(filters=None):
	data    = []
	columns = []
		
	columns  = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		("Employee ID") + ":Link/Employee:120",
		("Name")+ ":Data:150",
		("CID No. ") + ":Data: 110",
		("Bank ") + ":Data: 110",
		("A/C No.") + ":Data:120",
		("Amount")+ ":Currency:140",
		("Branch")+ ":Data:190"
	]

def get_data(filters):
	conditions, filters = get_conditions(filters)
	query = """select ss.employee, ss.employee_name, e.passport_number, ss.bank_name, ss.bank_account_no, ss.net_pay, ss.branch 
			from `tabSalary Slip` ss, 
			`tabEmployee` e
			where ss.employee = e.name and ss.docstatus = 1 {0} order by ss.employee, ss.month""".format(conditions)
	d1 = frappe.db.sql(query)

	return d1

def get_conditions(filters):
	conditions = ""
	if filters.get("month"):
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(filters.get("month")) + 1
		filters["month"] = month
		conditions += " and ss.month ={0}".format(month)
	
	if filters.get("fiscal_year"): conditions += " and ss.fiscal_year = \'" + str(filters.fiscal_year) + "\'"
	if filters.get("company"): conditions += " and ss.company = \'" + str(filters.company) + "\'"
	if filters.get("bank"): conditions += " and ss.bank_name = \'" + str(filters.bank) + "\'"
	
	return conditions, filters
