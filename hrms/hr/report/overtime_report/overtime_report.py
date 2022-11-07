# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate, flt
from frappe import msgprint, _
from calendar import monthrange


def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	if not data:
		return columns, data
	columns = get_columns(data)
	return columns, data

def get_columns(data):
	columns = [
		_("Employee ID") + ":Link/Overtime Application:150",
		_("Employee Name") + "::150",
		_("Branch") + "::150",
		_("From Date/Time") + "::150",
		_("To Date/Time") + "::150",
		_("Number of Hours") + "::100",
		_("Amount") + ":Currency:120",
	]
	return columns

def get_data(filters):
	conditions, filters = get_conditions(filters)
	data = frappe.db.sql("""
		SELECT 
			oa.employee, oa.employee_name, oa.branch,
			oai.from_date, oai.to_date, oai.number_of_hours, oa.total_amount
		FROM `tabOvertime Application` oa, `tabOvertime Application Item` oai
		WHERE oa.name = oai.parent
		AND oai.to_date >= '{from_date}'
		AND oai.from_date <= '{to_date}' {condition}
	""".format(from_date=filters.get("from_date"), to_date=filters.get("to_date"),condition=conditions))
	return data

def get_conditions(filters):
	conditions = ""
	if filters.branch:
		conditions += """and branch="{}" """.format(filters.branch)
	return conditions, filters
