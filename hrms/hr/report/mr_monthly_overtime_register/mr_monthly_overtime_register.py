# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate, flt
from frappe import msgprint, _
from calendar import monthrange

def execute(filters=None):
	if not filters:
		filters = {}

	conditions, filters = get_conditions(filters)
	columns = get_columns(filters)
	ot_map = get_overtime_list(conditions, filters)

	data = []
	for emp in sorted(ot_map):
		row = [emp, ot_map[emp]['person_name'], ot_map[emp]['id_card'], ot_map[emp]['unit']]

		total_hours = 0.0
		for day in range(filters["total_days_in_month"]):
			number_of_hours = ot_map[emp]["overtime"].get(day + 1, "None")

			if flt(number_of_hours) > 0:
				total_hours += flt(number_of_hours)

			row.append(number_of_hours)

		row += [total_hours]
		data.append(row)

	return columns, data
	

def get_columns(filters):
	columns = [
		_("MR Employee") + "::120", _("Name") + "::140", _("CID No") + "::120", _("Unit") + "::100"
	]

	for day in range(filters["total_days_in_month"]):
		columns.append(cstr(day + 1) + "::42")

	columns += [_("Total Hours") + ":Float:100"]
	return columns

def get_overtime_list(conditions, filters):
	overtime_list = frappe.db.sql("""select mr_employee, mr_employee_name, unit, 
		day(date) as day_of_month, number_of_hours from `tabMuster Roll Overtime Entry`
		where docstatus = 1 %s order by mr_employee, date""" % conditions, filters, as_dict=1)
	
	ot_map = {}
	for d in overtime_list:
		emp_id = d.mr_employee
		ot_map.setdefault(emp_id, {
			'person_name': d.mr_employee_name,
			'id_card': d.mr_employee,
			'unit': d.unit,
			'overtime': {}
		})
		ot_map[emp_id]['overtime'][d.day_of_month] = d.number_of_hours

	return ot_map

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
	year_list = frappe.db.sql_list("""select distinct YEAR(date) from `tabMuster Roll Overtime Entry` ORDER BY YEAR(date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)
