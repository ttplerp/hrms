# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_data(filters):
	conditions = get_conditions(filters)

	if filters.get('have_not_checkin'):
		if filters.get('late_checkin_out') == 1:
			frappe.throw("Uncheck value for Late CheckIn or EarlyExit")

		cond_shift = cond_dept = ''
		if filters.get('shift_type'):
			cond_shift = " and ci.shift = '{}'".format(filters.get('shift_type'))

		if filters.get('department'):
			cond_dept = " and e.department = '{}'".format(filters.get('department'))

		return frappe.db.sql(
			"""
			Select e.department, e.name as employee, e.employee_name as full_name
			From tabEmployee e 
			Where e.name NOT IN (
				Select distinct ci.employee 
				From `tabEmployee Checkin` ci
				Where ci.date between %(from_date)s AND %(to_date)s
					{cond_shift}
			)
			{cond_dept}
			""".format(
				cond_shift=cond_shift,
				cond_dept=cond_dept
			),
			filters,
			as_dict=1,
		)

	shift_type_condition = from_shift_type = ''
	if filters.get('late_checkin_out'):
		from_shift_type = ", `tabShift Type` st"
		shift_type_condition = " st.name=ci.shift and (ci.log_type='IN' and ci.time > st.start_time or \
			ci.log_type='OUT' and ci.time < st.end_time) and "
	return frappe.db.sql(
		"""
		Select e.department, e.name as employee, e.employee_name as full_name, ci.log_type, ci.date,
			case 
				when ci.log_type = 'IN' then ci.time
				else ""
			end as check_in,
			case 
				when ci.log_type = 'OUT' then ci.time
				else ""
			end as check_out,
			ci.shift as shift_type, ci.reason
		From tabEmployee e, `tabEmployee Checkin` ci {from_shift_type}
		Where e.name = ci.employee and
			{shift_type_condition}
			{conditions}
		Order By e.department, ci.date, e.name
		""".format(
			from_shift_type=from_shift_type,
			dept=str(filters.get('department')),
			shift_type_condition=shift_type_condition,
			conditions=conditions
		),
		filters,
		as_dict=1,
	)

def get_conditions(filters):
	conditions = (
		"ci.date between %(from_date)s AND %(to_date)s"
	)

	if filters.get('shift_type'):
		conditions += " and ci.shift = '{}'".format(filters.get('shift_type'))

	if filters.get('department'):
		conditions += " and e.department = '{}'".format(filters.get('department'))

	return conditions

def get_columns(filters):
	return [
		{
			"fieldname": "department",
			"label": "Department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 200
		},
		{
			"fieldname": "employee",
			"label": "Employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120
		},
		{
			"fieldname": "full_name",
			"label": "Full Name",
			"fieldtype": "Data",
			"width":160
		},
		{
			"fieldname": "date",
			"label": "Date",
			"fieldtype": "Date",
			"width":100
		},
		{
			"fieldname": "log_type",
			"label": "Log Type",
			"fieldtype": "Data",
			"width":50
		},
		{
			"fieldname": "check_in",
			"label": "Check In",
			"fieldtype": "time",
			"width":100
		},
		{
			"fieldname": "check_out",
			"label": "Check Out",
			"fieldtype": "time",
			"width":100
		},
		{
			"fieldname": "shift_type",
			"label": "Shift Type",
			"fieldtype": "Link",
			"options": "Shift Type",
			"width":120
		},
		{
			"fieldname": "reason",
			"label": "Reason",
			"fieldtype": "Data",
			"width":300,
			"align":"left"
		},
	]