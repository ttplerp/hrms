# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from frappe import _
import frappe
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_data(filters):
	conditions = get_conditions(filters)
	# data = frappe.db.sql("""
	# 	SELECT e.name, e.employee_name, e.passport_number, e.company_email, e.date_of_birth, e.cell_number, e.reports_to, e.reports_to_name,
	# 	e.department, e.division, e.section, e.employment_type, e.employee_group, e.grade, e.designation, e.employment_status, e.date_of_joining, e.status, e.increment_cycle, e.promotion_cycle, e.promotion_due_date, e.date_of_retirement, e.blood_group, ee.school_univ, ee.qualification, ee.level, ee.year_of_passing, ee.class_per, ee.maj_opt_subj
	# 	FROM `tabEmployee` e, `tabEmployee Education` as ee 
	# 	WHERE ee.parent = e.name
	# 	AND department is not null %s			
	# 	"""%conditions, filters)
	data = frappe.db.sql("""
		SELECT dal.employee, dal.employee_name, dal.posting_date, sum(dali.duration) as time_spent, dal.branch, dal.department, dal.division, dal.section, dal.unit, e.employment_type, e.employee_group,
		e.grade, dal.designation, e.reports_to, e.reports_to_name
		FROM `tabDaily Activity Log` dal, `tabDaily Activity Log Item` dali, `tabEmployee` e
		WHERE dal.name = dali.parent and dal.employee = e.name and e.status = 'Active' {}
		group by dal.posting_date, dal.employee order by dal.posting_date desc
		""".format(conditions))

	return data

def get_conditions(filters):
	conditions = ''
	if filters.get("employee"):
		conditions += f""" and dal.employee = '{filters.get("employee")}'"""
	if filters.get("department"):
		conditions += f""" and dal.department = '{filters.get("department")}'"""
	if filters.get("division"):
		conditions += f""" and dal.division = '{filters.get("department")}'"""
	if filters.get("unit"):
		conditions += f""" and dal.unit = '{filters.get("unit")}'"""
	if filters.get("from_date"):
		conditions += f""" and dal.posting_date >= '{filters.from_date}'"""
	if filters.get("to_date"):
		conditions += f""" and dal.posting_date <= '{filters.to_date}'"""
	return conditions

def get_columns(filters):
	columns =  [
		_("Employee ID") + ":Link/Employee:120",
		_("Employee Name") + ":Data:120",
		_("Date") + ":Date:120",
		_("Time Spent(Hours)") + ":Float:100",
		_("Branch") + ":Link/Branch:100",
		_("Department") + ":Link/Department:120",
		_("Division") + ":Link/Department:120",
		_("Section") + ":Link/Department:120",
		_("Unit") + ":Link/Department:120",
		_("Employee Type") + ":Data:120", 
		_("Employee Group") + ":Data:120", 
		_("Grade") + ":Data:60", 
		_("Designation") + ":Data:120",
		_("Supervisor ID") + ":Link/Employee:120",
		_("Supervisor") + ":Data:120"
    ]
	return columns
