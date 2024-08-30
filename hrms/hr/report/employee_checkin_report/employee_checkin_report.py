# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
import itertools
from frappe.utils import time_diff_in_hours, time_diff_in_hours

def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	emp_map = get_employees(filters)

	data = []
	#frappe.msgprint("{}".format(checkin_map))
	for a in emp_map:
		for emp in frappe.db.sql("""
                         select employee_name, branch, department, designation
                         from `tabEmployee`
                         where name = '{}'
                         """.format(a.employee), as_dict=True):
  			row = [a.employee, emp.employee_name, emp.branch, emp.department, emp.designation]

		office_in = lunch_out = lunch_in = office_out = '''<text style="color:red"><b>Not Punched</b></text>'''
		oi_reason = oo_reason = office_in_time = office_out_time = None
		checkin_map = get_checkin_list(filters, a.employee)
		for b in checkin_map:
			if b.att_date == a.att_date:
				if b.type == "Office" and b.log_type == "IN":
					office_in = b.att_time
					office_in_time = b.att_time_nf
					oi_reason = b.reason
				elif b.type == "Lunch" and b.log_type == "OUT":
					lunch_out = b.att_time
				elif b.type == "Lunch" and b.log_type == "IN":
					lunch_in = b.att_time
				elif b.type == "Office" and b.log_type == "OUT":
					office_out = b.att_time
					office_out_time = b.att_time_nf
					oo_reason = b.reason
   
		# row.extend([a.att_date, office_in, oi_reason, lunch_out, lunch_in, office_out, oo_reason])
		if office_in != """<text style="color:red"><b>Not Punched</b></text>""" and office_out != """<text style="color:red"><b>Not Punched</b></text>""":
			row.extend([a.att_date, office_in, oi_reason, office_out, oo_reason, time_diff_in_hours(office_out_time, office_in_time)])
		else:
			row.extend([a.att_date, office_in, oi_reason, office_out, oo_reason, 0])

		data.append(row)
	# frappe.msgprint(str(data))
	new_data = []
	for a in data:
		if a not in new_data:
			new_data.append(a)
	data = new_data
	#sorting the data based on date in descending
	data.sort(key=lambda r: r[5], reverse=True)
	return columns, data

def get_columns(filters):
	columns = [
		_("Employee") + "::100", _("Employee Name") + "::140", _("Branch")+ "::120",
		_("Department") + "::150", _("Designation") + "::150", _("Date") + "::100"
	]

	# columns += [_("Office In") + ":Data:100", _("Late Punching") + ":Data:150", _("Lunch Out") + ":Data:100", _("Lunch In") + ":Data:100", _("Office Out") + ":Data:100", _("Early Exit") + ":Data:150"]
	columns += [_("Office In") + ":Data:100", _("Late Punching") + ":Data:150", _("Office Out") + ":Data:100", _("Early Exit") + ":Data:90", _("Total Hours") + ":Float:150"]
	
	return columns

def get_checkin_list(filters, employee):
	return frappe.db.sql("""select ec.employee, ec.type,ec.log_type,
			ec.date as att_date, time_format(ec.time, "%H:%i %p") as att_time, ec.time as att_time_nf, ec.reason
			from `tabEmployee Checkin` ec
   			where ec.date between '{from_date}' and '{to_date}'
			and ec.employee = '{employee}'
			order by ec.employee, ec.creation, ec.date
   			""".format(from_date=filters.get("from_date"), to_date=filters.get("to_date"), employee = employee), as_dict=1)

def get_conditions(filters):
	cond = ""
	if filters.employee:
		cond += """ and employee="{}" """.format(filters.employee)
	return cond

def get_employees(filters):
    cond = get_conditions(filters)
    return frappe.db.sql("""select employee, ec.date as att_date
		from `tabEmployee Checkin` ec
		where ec.date between '{from_date}' and '{to_date}' {condition}
		order by ec.employee
		""".format(from_date=filters.get("from_date"), to_date=filters.get("to_date"),condition=cond), as_dict=1)
