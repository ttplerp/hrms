# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
# ------------------------------------------------------------
# Date				Description							Author
# Oct-31-2020			Added a unit filter and field					Phuntsho
# ------------------------------------------------------------
from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate
from frappe import msgprint, _
from calendar import monthrange

def execute(filters=None):
	if not filters: filters = {}

	conditions, filters = get_conditions(filters)
	columns = get_columns(filters)
	att_map = get_attendance_list(conditions, filters)
	emp_map = get_employee_details(filters.employee_type, filters)
	data = []
	for emp in sorted(att_map):
		emp_det = emp_map.get(emp)
		
		if not emp_det:
			continue

		row = [emp_det.person_name, emp_det.id_card, emp_det.unit]

		total_p = total_a = 0.0
		for day in range(filters["total_days_in_month"]):
			status = att_map.get(emp).get(day + 1, "None")
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
		_("Name") + "::140", _("CID")+ "::120", _("Unit")+"::100"
	]

	for day in range(filters["total_days_in_month"]):
		columns.append(cstr(day+1) +"::20")

	columns += [_("Total Present") + ":Float:100", _("Total Absent") + ":Float:100"]
	return columns

def get_attendance_list(conditions, filters):
	sql = """select mr_employee, day(date) as day_of_month,
		status from `tabMuster Roll Attendance` where docstatus = 1 %s order by mr_employee, date""" %conditions, filters
	attendance_list = frappe.db.sql("""
		select mr_employee, day(date) as day_of_month,
		status from `tabMuster Roll Attendance` where docstatus = 1 %s 
		order by mr_employee, date""" %conditions, filters, as_dict=1)

	att_map = {}
	for d in attendance_list:
		att_map.setdefault(d.mr_employee, frappe._dict()).setdefault(d.day_of_month, "")
		att_map[d.mr_employee][d.day_of_month] = d.status

	return att_map

def get_conditions(filters):
	if not (filters.get("month") and filters.get("year")):
		msgprint(_("Please select month and year"), raise_exception=1)

	filters["month"] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
		"Dec"].index(filters.month) + 1

	filters["total_days_in_month"] = monthrange(cint(filters.year), filters.month)[1]

	conditions = " and month(date) = %(month)s and year(date) = %(year)s and cost_center = \'" + str(filters.cost_center) + "\' "

	return conditions, filters


def get_employee_details(employee_type,filters):
	emp_map = frappe._dict()
	if employee_type == "Muster Roll Employee":
		# added unit by phuntsho on oct 30
		for d in frappe.db.sql("""select name, person_name, id_card, unit
			from `tabMuster Roll Employee`""", as_dict=1):
			emp_map.setdefault(d.name, d)
	# elif employee_type == "DES Employee":
	# 	for d in frappe.db.sql("""select name, person_name, id_card
	# 		from `tabDES Employee`""", as_dict=1):
	# 		emp_map.setdefault(d.name, d)
	else:
		frappe.throw("Select a Employee Type")
	return emp_map

@frappe.whitelist()
def get_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(date) from `tabMuster Roll Attendance` ORDER BY YEAR(date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)
