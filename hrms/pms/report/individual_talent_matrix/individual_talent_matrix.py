# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _

def execute(filters=None):
	if not filters:
		filters = {}
	columns, data = [], []
	data = get_data(filters)
	if not data:
		return columns, data
	columns = get_columns(data, filters)
	return columns, data

def get_conditions(filters):
	conditions = ''
	if filters.get("from_month"):
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(filters["from_month"]) + 1
		filters["from_month"] = month
		conditions += " and month >= %(from_month)s"
	
	if filters.get("to_month"):
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(filters["to_month"]) + 1
		filters["to_month"] = month
		conditions += " and month <= %(to_month)s"

	if filters.get("fiscal_year"):
		conditions += " and fiscal_year = %(fiscal_year)s"

	if filters.get("exclude_muster_roll") == 1:
		conditions += " and for_muster_roll_employee = 0"

	return conditions, filters

def get_data(filters):
	conditions, filters = get_conditions(filters)
	data = []
	evaluation_data = []
	pre_data = {}
	evaluation_data = frappe.db.sql("""
							SELECT (CASE WHEN p.for_muster_roll_employee = 1 THEN p.mr_employee ELSE p.employee END) as employee, p.fiscal_year, p.month, i.competency, i.evaluator, p.name  
					  		from `tabPerformance Evaluation` as p
					  		inner join `tabEvaluate Competency Item` i
					  		on i.parent = p.name and p.employee = '20230523211'
					  		where p.docstatus = 1 %s
						"""%conditions, filters, as_dict=True)
	
	for a in evaluation_data:
		if str(a.employee)+'-'+str(a.fiscal_year) not in pre_data:
			pre_data.update({str(a.employee)+'-'+str(a.fiscal_year): {str(a.name): { "count": 1, "score": a.evaluator, a.competency: a.evaluator}}})
		else:
			if a.name not in pre_data[a.employee+"-"+a.fiscal_year]:
				pre_data[str(a.employee)+'-'+str(a.fiscal_year)].update({str(a.name): { "count": 1, "score": a.evaluator, a.competency: a.evaluator}})	
			else:
				pre_data[str(a.employee)+'-'+str(a.fiscal_year)][a.name]["count"] += 1
				pre_data[str(a.employee)+'-'+str(a.fiscal_year)][a.name]["score"] += 1
			# 	pre_data[str(a.employee)+'-'+str(a.fiscal_year)][a.name][a.competency] = pre_data[str(a.employee)+'-'+str(a.fiscal_year)][a.name]["score"]/pre_data[str(a.employee)+'-'+str(a.fiscal_year)][a.name]["count"]



	
	frappe.throw(str(pre_data))	
	frappe.throw(str(evaluation_data))

	for p in pre_data:
		potential = 0
		performance = 0
		pot = 0
		per = 0
		''''
			COMPETENCY									CATEGORY
			1. Job Knowledge /Technical Skills			Potential
			2. Productivity & Use of Time				Performance
			3. Quality of Work							Performance
			4. Initiative & Responsibility				Potential 
		'''
		for i in pre_data[p]:
			if i in ['Initiative & Responsibility', 'Job Knowledge/Technical Skills']:
				potential += flt(pre_data[p][i])
				pot += 1
			elif i in ['Productivity & Use of Time', 'Quality of Work']:
				performance += flt(pre_data[p][i])
				per += 1
		
		if potential != 0:
			potential = potential/pot
		if performance != 0:
			performance = performance/per

		frappe.throw(str(pot)+' '+str(per))

		# frappe.throw(str(potential)+' '+str(performance))

		pot_per = determine_pot_per(potential, performance)

		employee = str(p).split('-')[0]
		if not frappe.db.exists("Employee", {"employee": employee}):
			emp_name = frappe.db.get_value("Muster Roll Employee", employee, "person_name")
			designation = frappe.db.get_value("Muster Roll Employee", employee, "designation")
			branch = frappe.db.get_value("Muster Roll Employee", employee, "branch")
			education_level = "NULL"
			employee_qualification = frappe.db.get_value("Employee", employee, "employee_qualification")
			date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
			employment_type = frappe.db.get_value("Employee", employee, "employment_type")
		else:
			emp_name = frappe.db.get_value("Employee", employee, "employee_name")
			designation = frappe.db.get_value("Employee", employee, "designation")
			branch = frappe.db.get_value("Employee", employee, "branch")
			education_level = frappe.db.get_value("Employee", employee, "education_level")
			employee_qualification = frappe.db.get_value("Employee", employee, "employee_qualification")
			date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
			employment_type = frappe.db.get_value("Employee", employee, "employment_type")

		if filters.get("pot_per") == pot_per:
			data.append({
				'employee': employee,
				'emp_name': emp_name,
				'designation': designation,
				'branch': branch,
				'education_level': education_level,
				'employee_qualification': employee_qualification,
				'date_of_joining': date_of_joining,
				'employment_type': employment_type,
			})
			
	return data

def is_between(a, x, b):
	return min(a, b) <= x <= max(a, b)

def determine_pot_per(potential, performance):
	total_score = 0.0
	return_value = ''
	total_score = flt(performance + potential)
	if is_between(5.1, total_score, 6) and potential > performance:
		return_value = "Unrealized Performer"
	elif is_between(6.1, total_score, 7.5) and potential > performance:
		return_value = "Growth Employee"
	elif is_between(7.6, total_score, 8):
		return_value = "Future Senior Leader"
	elif is_between(4.1, total_score, 5) and potential > performance:
		return_value = "Inconsistent Performer"
	elif potential == 3 and performance == 3:
		return_value = "Core Employee"
	elif is_between(6.1, total_score, 7.5) and potential < performance:
		return_value = "High-Impact Performer"
	elif total_score < 4:
		return "Low Performer"
	elif is_between(4.1, total_score, 5) and potential < performance:
		return "Effective Employee"
	elif is_between(5.1, total_score, 6) and potential < performance:
		return "Trusted Professional"
	return return_value

def get_columns(data, filters):
	columns = [
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Data", "width": 130},
		{"label": _("Employee Name"), "fieldname": "emp_name", "fieldtype": "Data", "width": 150},
		{"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 150},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 150},
		{"label": _("Education Level"), "fieldname": "education_level", "fieldtype": "Link", "options": "Education Level", "width": 150},
		{"label": _("Employee Qualification"), "fieldname": "employee_qualification", "fieldtype": "Data", "width": 150},
		{"label": _("Joining Date"), "fieldname": "date_of_joining", "fieldtype": "Date", "width": 120},
		{"label": _("Employment Type"), "fieldname": "employement_type", "fieldtype": "Link", "options": "Employement Type", "width": 120},
	]

	return columns
