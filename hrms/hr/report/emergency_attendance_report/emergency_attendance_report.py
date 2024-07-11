# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, flt, cint

def execute(filters=None):
	columns, data = [], []
	columns = get_columns(data)
	queries = construct_query(filters)
	data = get_data(queries,filters)

	return columns, data

def get_columns(data):
	return [
		{
			"fieldname": "name",
			"label": "Transaction ID",
			"fieldtype": "Link",
			"options": "Emergency Attendance",
			"width": 100
		},
		{
			"fieldname": "employee",
			"label": "Employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 100
		},
		{
			"fieldname": "full_name",
			"label": "Full Name",
			"fieldtype": "Data",
			"width":150
		},
		{
			"fieldname": "branch",
			"label": "Branch",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 200
		},
		{
			"fieldname": "check_in",
			"label": "Check In",
			"fieldtype": "Data",
			"width":100
		},
		{
			"fieldname": "check_out",
			"label": "Check Out",
			"fieldtype": "Data",
			"width":100
		},
		{
			"fieldname": "total_working_hr",
			"label": "Total Working Hr",
			"fieldtype": "Data",
			"width":100
		},
		{
			"fieldname": "reason",
			"label": "Reason",
			"fieldtype": "Data",
			"width":300
		},
	]
def construct_query(filters=None):
	conditions, filters = get_conditions(filters)
	query = ("""select name, employee, employee_name, branch, check_in, check_out, total_working_hr, reason
			from `tabEmergency Attendance`
			where docstatus = 1
			and posting_date between '{0}' and '{1}'
			{2}
		""".format(filters.get("from_date"),filters.get("to_date"),conditions))
	return query	

def get_data(query, filters):
	data = []
	datas = frappe.db.sql(query, as_dict=True)
	# frappe.msgprint(str(datas))
	for d in datas:
		row = {
			"name": d.name,
			"employee": d.employee,
			"full_name":d.employee_name,
			"branch": d.branch,
			"check_in": d.check_in,
			"check_out":d.check_out,
			"total_working_hr":d.total_working_hr,
			"reason":d.reason,
		}
		data.append(row)
	return data
def get_conditions(filters):
	conditions = ""
	if filters.get("branch"):
		conditions += """and branch ='{}'""".format(filters.get("branch"))
	if filters.get("employee"):
		conditions += """and employee ='{}'""".format(filters.get("employee"))
	return conditions, filters
