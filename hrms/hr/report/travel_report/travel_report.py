# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	if not data:
		return columns, data
	columns = get_columns(data)
	return columns, data

def get_columns(data):
	columns = [
		_("Employee ID") + ":Link/Employee:120",
        _("Employee") + ":Data:120",
        _("EX Claim") + ":Link/Expense Claim:180",
        _("Travel Request") + ":Link/Travel Request:180",
        _("Designation") + ":Data:180",
        _("Cost Center") + ":Data:160",
        _("Department") + ":Data:160",
        _("From Date") + ":Date:100",
        _("To Date") + ":Date:100",
        _("No of Dyas") + ":Data:100",
        _("EX Date") + ":Date:100",
        _("EX Type") + ":Data:100",
        _("DSA Per Day") + ":Data:120",
        _("Total Claim") + ":Currency:120",
        _("Status") + ":Data:120"
	]
	return columns

def get_data(filters):
	conditions, filters = get_conditions(filters)
	data = frappe.db.sql("""
		select 
			ec.employee, ec.employee_name, ec.name, ecd.reference, e.designation, e.cost_center, ec.department,
			min(ti.from_date) as min,
			max((case when ti.halt = 1 then ti.to_date when ti.halt = 0 then ti.to_date end)) as max,
			sum(ti.no_days_actual) as no_of_days,  
			ecd.expense_date, ecd.expense_type, tr.dsa_per_day, ec.total_claimed_amount, ec.status  
		from `tabExpense Claim` ec, `tabEmployee` e, `tabExpense Claim Detail` ecd, `tabTravel Request` tr, `tabTravel Itinerary` ti 
		where ecd.parent = ec.name 
			and e.name = ec.employee
			and ecd.reference = tr.name
			and tr.name = ti.parent
			and ec.docstatus = 1 %s
			and ecd.expense_type = 'Travel'
			group by ec.name
		"""% conditions, filters)
	return data

def get_conditions(filters):
	conditions = ""
	if filters.get("employee"): 
		conditions += " and ec.employee = %(employee)s"

	if filters.get("from_date") and filters.get("to_date"):
		conditions += " and ec.posting_date between  '{0}' and '{1}'".format(filters.get("from_date"), filters.get("to_date"))

	if filters.get("cost_center"): conditions += " and exists(select 1 from `tabCost Center` cc where ec.cost_center = cc.name and (cc.parent_cost_center = '{0}' or cc.name = '{0}'))".format(filters.cost_center)

	return conditions, filters