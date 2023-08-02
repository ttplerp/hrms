# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _


def execute(filters=None):
	if not filters:
		filters = {}

	columns, data = [], []
	data =  get_data(filters)
	if not data:
		return columns, data
	columns = get_columns(data)
	return columns, data

def get_conditions(filters):
	conditions = ''
	if filters.get("employee"):
		conditions += " and employee = %(employee)s"
	return conditions, filters


def get_data(filters):
	conditions, filters = get_conditions(filters)
	data = frappe.db.sql("""
			select evaluator, evaluator_name, employee, employee_name, evaluator_score from `tabPerformance Evaluation` where docstatus = 1 %s
			"""%conditions, filters)
	return data

def get_columns(filters):
	columns =  [
		_("Evaluator ID") + ":Link/Employee:120",
		_("Evaluator Name") + ":Data:140",
		_("Employee ID") + ":Link/Employee:120",
		_("Employee Name") + ":Data:140",
		_("Point") + ":Data:140",
	]
	return columns
