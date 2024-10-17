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
	
	if filters.get("employee_group"):
		conditions += " and employee_group = %(employee_group)s"

	if filters.get("exclude_muster_roll") == 1:
		conditions += " and for_muster_roll_employee = 0"

	return conditions, filters

def validate_active_employee(evaluation_data):
	validate_data = []

	
	for row in evaluation_data:
		employee = row.get('employee')
		
		# Check if it's an active employee in Muster Roll Employee or Employee Doctype
		if not frappe.db.exists("Employee", {"employee": employee}):
			status = frappe.db.get_value("Muster Roll Employee", {"name": employee}, "status")
		else:
			status = frappe.db.get_value("Employee", {"name": employee}, "status")
		
		# Consider active only if status is "Active"
		if status == "Active":
			validate_data.append(row)
	
	return validate_data

def get_data(filters):
	conditions, filters = get_conditions(filters)
	data = []
	evaluation_data = []
	pre_data = {}

	evaluation_data = frappe.db.sql("""
							SELECT (CASE WHEN p.for_muster_roll_employee = 1 THEN p.mr_employee ELSE p.employee END) as employee, p.fiscal_year, p.month, i.competency, i.evaluator, p.name  
					  		from `tabPerformance Evaluation` as p
					  		inner join `tabEvaluate Competency Item` i
					  		on i.parent = p.name
					  		where p.docstatus = 1 %s
						"""%conditions, filters, as_dict=True)
	
	if filters.get("is_active"):
		evaluation_data = validate_active_employee(evaluation_data)
	
	for a in evaluation_data:
		if str(a.employee)+'-'+str(a.fiscal_year) not in pre_data:
			pre_data.update({str(a.employee)+'-'+str(a.fiscal_year): {str(a.name): { a.competency: a.evaluator}}})
		else:
			if a.name not in pre_data[a.employee+"-"+a.fiscal_year]:
				pre_data[str(a.employee)+'-'+str(a.fiscal_year)].update({str(a.name): { a.competency: a.evaluator}})	
			else:
				pre_data[str(a.employee)+'-'+str(a.fiscal_year)][a.name][a.competency] = a.evaluator
	
	# frappe.throw(str(pre_data))
	for p in pre_data:
		employee = str(p).split('-')[0]

		if not frappe.db.exists("Employee", {"employee": employee}):
			pms_group = frappe.db.get_value("Muster Roll Employee", employee, "pms_employee_group")
		else:
			pms_group = frappe.db.get_value("Employee", employee, "employee_group")

		potential = 0
		performance = 0
		pot = 0
		per = 0
		''''
			COMPETENCY (General Staff)					CATEGORY
			1. Job Knowledge/Technical Skills			Potential
			2. Productivity & Use of Time				Performance
			3. Quality of Work							Performance
			4. Initiative & Responsibility				Potential 

			Managers
			1. Performance Management					Potential
			2. Planning & Orgainizing Skills			Performance
			3. Supervisory Leadership					Performance
			4. Sense of Ownership						Potential
		'''
		if pms_group == "Supervisory & Managerial":
			for i in pre_data[p]:
				for a in pre_data[p][i]:
					if a in ['Performance Management', 'Sense of Ownership']:
						potential += flt(pre_data[p][i][a])
						pot += 1
					elif a in ['Planning & Organizing Skills', 'Supervisory & Leadership']:
						performance += flt(pre_data[p][i][a])
						per += 1
		else:
			for i in pre_data[p]:
				for a in pre_data[p][i]:
					if a in ['Initiative & Responsibility', 'Job Knowledge/Technical Skills']:
						potential += flt(pre_data[p][i][a])
						pot += 1
					elif a in ['Productivity & Use of Time', 'Quality of Work']:
						performance += flt(pre_data[p][i][a])
						per += 1
		if potential != 0:
			potential = flt(potential/pot, 1)
		if performance != 0:
			performance = flt(performance/per, 1)
		# frappe.msgprint(str(potential)+' '+str(performance))
		pot_per = determine_pot_per(potential, performance)

		if not frappe.db.exists("Employee", {"employee": employee}):
			emp_name = frappe.db.get_value("Muster Roll Employee", employee, "person_name")
			designation = frappe.db.get_value("Muster Roll Employee", employee, "designation")
			branch = frappe.db.get_value("Muster Roll Employee", employee, "branch")
			date_of_joining = frappe.db.get_value("Muster Roll Employee", employee, "joining_date")
			employment_type = frappe.db.get_value("Muster Roll Employee", employee, "muster_roll_type")
		else:
			emp_name = frappe.db.get_value("Employee", employee, "employee_name")
			designation = frappe.db.get_value("Employee", employee, "designation")
			branch = frappe.db.get_value("Employee", employee, "branch")
			date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
			employment_type = frappe.db.get_value("Employee", employee, "employment_type")

		if filters.get("pot_per") == pot_per:
			data.append({
				'employee': employee,
				'emp_name': emp_name,
				'designation': designation,
				'branch': branch,
				'date_of_joining': date_of_joining,
				'performance': flt(performance, 1),
				'potential': flt(potential, 1),
				'total_score': flt(performance+potential, 1),
				'employment_type': employment_type,
			})
			
	return data

def is_between(a, x, b):
	return min(a, b) <= x <= max(a, b)

def determine_pot_per(potential, performance):
	total_score = 0.0
	return_value = ''
	total_score = flt(performance + potential)
	if is_between(5.5, total_score, 6.4) and potential > performance:
		return_value = "Unrealized Performer"
	elif is_between(6.5, total_score, 7.4) and potential > performance:
		return_value = "Growth Employee"
	elif is_between(7.5, total_score, 8):
		return_value = "Future Senior Leader"
	elif is_between(4.5, total_score, 5.4) and potential > performance:
		return_value = "Inconsistent Performer"
	elif is_between(5.5, total_score, 6.4) and potential == performance:
		return_value = "Core Employee"
	elif is_between(6.5, total_score, 7.4) and potential < performance:
		return_value = "High-Impact Performer"
	elif total_score < 4.4:
		return "Low Performer"
	elif is_between(4.5, total_score, 5.4) and potential < performance:
		return "Effective Employee"
	elif is_between(5.5, total_score, 6.4) and potential < performance:
		return "Trusted Professional"
	return return_value

def get_columns(data, filters):
	columns = [
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Data", "width": 130},
		{"label": _("Employee Name"), "fieldname": "emp_name", "fieldtype": "Data", "width": 150},
		{"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 150},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 150},
		{"label": _("Perfromacne"), "fieldname": "performance", "fieldtype": "Data", "width": 120},
		{"label": _("Potential"), "fieldname": "potential", "fieldtype": "Data", "width": 120},
		{"label": _("Total Score"), "fieldname": "total_score", "fieldtype": "Data", "width": 120},
		{"label": _("Joining Date"), "fieldname": "date_of_joining", "fieldtype": "Date", "width": 120},
		{"label": _("Employment Type"), "fieldname": "employment_type", "fieldtype": "Data", "width": 120},

	]

	return columns
