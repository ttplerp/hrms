# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe


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
	att_map = get_attendance_list(conditions, filters)
	emp_map = get_employee_details(filters.employee_type)

	data = []
	for emp in sorted(att_map):
		emp_det = emp_map.get(emp)
		if not emp_det:
			continue

		row = [emp_det.person_name, emp_det.id_card, emp_det.cost_center]

		total_p = 0.0
		for day in range(filters["total_days_in_month"]):
			for t in ("R","S"):
				status = att_map.get(emp).get(str(day + 1)+str(t), '')

				if flt(status) > 0:
					total_p += flt(status)

				row.append(status)

		row += [total_p]
		data.append(row)

	return columns, data

def get_columns(filters):
	columns = [
		_("Name") + "::140", _("CID")+ "::120", _("Cost Center") + ":Link/Cost Center:100"
	]

	for day in range(filters["total_days_in_month"]):
		columns.append(cstr(day+1)+"R" +"::35")
		columns.append(cstr(day+1)+"S" +"::35")

	columns += [_("Total Hours") + ":Float:100"]
	return columns

def get_attendance_list(conditions, filters):
	attendance_list = frappe.db.sql(f"""select mr_employee as employee, day(date) as day_of_month, cost_center,
					number_of_hours_regular as status, number_of_hours_special as hrs 
				from `tabMuster Roll Overtime Entry` where docstatus = 1 %s order by mr_employee, date""" %
		conditions, filters, as_dict=1)

	att_map = {}
	for d in attendance_list:
		for t in ("R","S"):
			day_of_month = str(d.day_of_month) + str(t)
			att_map.setdefault(d.employee, frappe._dict()).setdefault(day_of_month, "")
			att_map[d.employee][day_of_month] = d.status if t=="R" else d.hrs
			att_map[d.employee]["cost_center"] = d.cost_center
	return att_map

def get_conditions(filters):
	if not (filters.get("month") and filters.get("year")):
		msgprint(_("Please select month and year"), raise_exception=1)

	filters["month"] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
		"Dec"].index(filters.month) + 1

	filters["total_days_in_month"] = monthrange(cint(filters.year), filters.month)[1]

	conditions = " and month(date) = %(month)s and year(date) = %(year)s"
	if filters.get("cost_center"):
		conditions += " and cost_center = \'" + str(filters.cost_center) + "\' "
	return conditions, filters

def get_employee_details(employee_type):
	emp_map = frappe._dict()
	if employee_type == "Muster Roll Employee":
		for d in frappe.db.sql("""select name, person_name, id_card, cost_center
			from `tabMuster Roll Employee`""", as_dict=1):
			emp_map.setdefault(d.name, d)
	else:
		frappe.throw("Select a Employee Type")

	return emp_map

@frappe.whitelist()
def get_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(date) from `tabMuster Roll Overtime Entry` ORDER BY YEAR(date) DESC""")
	if not year_list:
		year_list = [getdate().year]
	
	return "\n".join(str(year) for year in year_list)