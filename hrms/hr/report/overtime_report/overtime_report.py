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
		_("Employee ID") + ":Link/Overtime Application:130",
		_("Employee Name") + "::150",
		_("Branch") + ":Link/Branch:150",
		_("Designation") + ":Link/Designation:120",
		_("Grade") + ":Link/Employee Grade:100",
		_("From Date/Time") + "::150",
		_("To Date/Time") + "::150",
		_("No. of Hours") + "::130",
		_("Amount") + ":Currency:120",
	]
	return columns

def get_data(filters):
	conditions = get_conditions(filters)
	data = frappe.db.sql("""
		SELECT 
			oa.employee, oa.employee_name, oa.branch, oa.designation, oa.grade, 
			oai.from_date, oai.to_date, ROUND(oai.number_of_hours,2), ROUND(oa.total_amount,2)
		FROM `tabOvertime Application` oa, `tabOvertime Application Item` oai
		WHERE oa.name = oai.parent
		AND oai.to_date >= '{from_date}'
		AND oai.from_date <= '{to_date}' {condition}
	""".format(from_date=filters.get("from_date"), to_date=filters.get("to_date"),condition=conditions))
	return data

def get_conditions(filters):
	conditions = ""
	if filters.get("branch"):
		conditions += "and oa.branch='{}' ".format(filters.get("branch"))
	if filters.get("employee"):
		conditions += " and oa.employee = '{}' ".format(filters.get("employee"))
	return conditions
