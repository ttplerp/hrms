# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

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
		_("Employee") + ":Link/Employee:120", 
		_("Employee Name") + "::140",
		_("Branch") + ":Link/Branch:120", 
		_("Advance Amount") + ":Currency:120", 
		_("No Of Installments") + ":Data:80", 
		_("Monthly Deduction") + ":Currency:120", 
		_("Date") + ":Date:80", 
		_("Recovered Amount") + ":Currency:120", 
		_("Balance") + ":Currency:120"
	]

	return columns

def get_data(filters):
	conditions, filters = get_conditions(filters)

	data = frappe.db.sql("""
		select x.*, ifnull(x.paid_amount,0) - ifnull(x.total_collected,0) as balance
		from (
			select 
				ea.employee, ea.employee_name, 
				ea.branch, ea.paid_amount, ea.deduction_month, ea.monthly_deduction, ea.posting_date,
				(select sum(sd.amount)
				from `tabSalary Detail` sd
				where sd.reference_number = ea.name
				and sd.docstatus = 1
				) total_collected
			from `tabEmployee Advance` ea
			where ea.docstatus = 1 %s
		) x
		""" % conditions, filters)

	return data

def get_conditions(filters):
	conditions = ""
	if filters.get("from_date") and filters.get("to_date"):
		conditions += " and ea.posting_date between %(from_date)s and %(to_date)s"
	if filters.get("employee"): conditions += " and ea.employee = %(employee)s"

	return conditions, filters
