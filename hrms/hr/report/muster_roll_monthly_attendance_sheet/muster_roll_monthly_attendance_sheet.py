# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate
from frappe import msgprint, _
from calendar import monthrange

def execute(filters=None):
	if not filters:
		filters = {}

	conditions, filters = get_conditions(filters)
	columns = get_columns(filters)
	att_map = get_attendance_list(conditions, filters)

	data = []
	for emp in sorted(att_map):
		row = [emp, att_map[emp]['person_name'], att_map[emp]['id_card'], att_map[emp]['unit']]

		total_p = total_a = 0.0
		for day in range(filters["total_days_in_month"]):
			status = att_map[emp]["attendance"].get(day + 1, "None")
			status_map = {"Present": "P", "Absent": "A", "None": ""}
			row.append(status_map[status])

			if status == "Present":
				total_p += 1
			elif status == "Absent":
				total_a += 1

		row += [total_p, total_a]
		data.append(row)

	return columns, data

def get_columns(filters):
	columns = [
		_("Employee") + "::120", _("Name") + "::140", _("CID") + "::120", _("Unit") + "::100"
	]

	for day in range(filters["total_days_in_month"]):
		columns.append(cstr(day + 1) + "::42")

	columns += [_("Total Present") + ":Float:100", _("Total Absent") + ":Float:100"]
	return columns

def get_attendance_list(conditions, filters):
	attendance_list = frappe.db.sql("""select mr_employee, mr_employee_name, unit, 
		day(date) as day_of_month, status from `tabMuster Roll Attendance`
		where docstatus = 1 %s order by mr_employee, date""" % conditions, filters, as_dict=1)
	
	att_map = {}
	for d in attendance_list:
		emp_id = d.mr_employee
		att_map.setdefault(emp_id, {
			'person_name': d.mr_employee_name,
			'id_card': d.mr_employee,
			'unit': d.unit,
			'attendance': {}
		})
		att_map[emp_id]['attendance'][d.day_of_month] = d.status

	return att_map

def get_conditions(filters):
	if not (filters.get("month") and filters.get("year")):
		msgprint(_("Please select month and year"), raise_exception=1)

	filters["month"] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(filters.month) + 1
	filters["total_days_in_month"] = monthrange(cint(filters.year), filters.month)[1]

	conditions = " and month(date) = %(month)s and year(date) = %(year)s and cost_center = \'" + str(filters.cost_center) + "\' "
	if filters.get("unit"):
		conditions += " and unit = \'" + str(filters.unit) + "\' "

	return conditions, filters

@frappe.whitelist()
def get_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(date) from `tabMuster Roll Attendance` ORDER BY YEAR(date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)
