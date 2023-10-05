# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _
from frappe import _, scrub

def execute(filters=None):
	if not filters:
		filters = {}

	columns, data = [], []
	data =  get_data(filters)
	if not data:
		return columns, data
	columns = get_columns(data, filters)
	return columns, data

def get_conditions(filters):
	conditions = ''
	if filters.get("employee"):
		conditions += " and employee = %(employee)s"
	if filters.get("mr_employee"):
		conditions += " and mr_employee = %(mr_employee)s"
	if filters.get("branch"):
		conditions += " and branch = %(branch)s"
	if filters.get("document_type") == "Employee":
		conditions += " and for_muster_roll_employee = 0"
	if filters.get("document_type") == "Muster Roll Employee":
		conditions += " and for_muster_roll_employee = 1"
	return conditions, filters

def get_data(filters):
	conditions, filters = get_conditions(filters)
	data = []
	pre_data = {}
	evaluation_data = frappe.db.sql("""
			select 
			fiscal_year,
			month,
			evaluator,
			evaluator_name,
			mr_employee,
			employee,
			employee_name,
			evaluator_score from `tabPerformance Evaluation` where docstatus = 1 %s
			"""%conditions, filters, as_dict=True)
	if not filters.get("overall"):
		for a in evaluation_data:
			if not a.mr_employee:
				if str(a.evaluator)+"-"+str(a.employee)+"-"+str(a.fiscal_year) not in pre_data:
					pre_data.update({str(a.evaluator)+"-"+str(a.employee)+"-"+a.fiscal_year: [{"score":a.evaluator_score, "month":a.month}]})
				else:
					pre_data[a.evaluator+"-"+a.employee+"-"+a.fiscal_year].append({"score":a.evaluator_score, "month":a.month})
			else:
				if str(a.evaluator)+"-"+str(a.mr_employee)+"-"+str(a.fiscal_year) not in pre_data:
					pre_data.update({str(a.evaluator)+"-"+str(a.mr_employee)+"-"+a.fiscal_year: [{"score":a.evaluator_score, "month":a.month}]})
				else:
					pre_data[a.evaluator+"-"+a.mr_employee+"-"+a.fiscal_year].append({"score":a.evaluator_score, "month":a.month})

		count = 0
		for b in pre_data:
			avg = 0.0
			c = 0
			for a in pre_data[b]:
				avg += flt(a.get('score')) if a.get('score') else 0
				if a.get('score'): 
					c +=1
			avg = avg/c
			
			evaluator, employee, fiscal_year = str(b).split("-")[0], str(b).split("-")[1], str(b).split("-")[2]
			if not frappe.db.exists("Employee", {"employee": employee}):
				emp_name = frappe.db.get_value("Muster Roll Employee", employee, "person_name")
			else:
				emp_name = frappe.db.get_value("Employee", employee, "employee_name")
				
			if not frappe.db.exists("Employee", {"employee": evaluator}):
				evaluator_name = frappe.db.get_value("Muster Roll Employee", evaluator, "person_name")
				evaluator_designation = frappe.db.get_value("Muster Roll Employee", evaluator, "designation")
			else:
				evaluator_name = frappe.db.get_value("Employee", evaluator, "employee_name")
				evaluator_designation = frappe.db.get_value("Employee", evaluator, "designation")

			data.append({"fiscal_year": fiscal_year, "evaluator": evaluator, "evaluator_name": evaluator_name, "evaluator_designation": evaluator_designation, "employee": employee, "emp_name": emp_name, 'average': flt(avg,2)})
			for c in pre_data[b]:
				month_field = get_period(int(flt(c.get('month'))))
				data[count][scrub(month_field)]=flt(c.get('score'),2) if c.get('score') else 0
			count+=1
	else:
		for a in evaluation_data:
			if not a.mr_employee:
				if str(a.employee)+"-"+str(a.fiscal_year) not in pre_data:
					pre_data.update({str(a.employee)+"-"+str(a.fiscal_year): {str(a.month):{"count": 1, "score": a.evaluator_score,"average":a.evaluator_score}}})
				else:
					if str(a.month) not in pre_data[a.employee+"-"+a.fiscal_year]:
						pre_data[a.employee+"-"+a.fiscal_year].update({str(a.month):{"count": 1, "score": a.evaluator_score, "average":a.evaluator_score}})
					else:
						pre_data[a.employee+"-"+a.fiscal_year][a.month]["count"]   += 1
						pre_data[a.employee+"-"+a.fiscal_year][a.month]["score"]   += a.evaluator_score
						pre_data[a.employee+"-"+a.fiscal_year][a.month]["average"] = pre_data[a.employee+"-"+a.fiscal_year][a.month]["score"]/pre_data[a.employee+"-"+a.fiscal_year][a.month]["count"]
			else:
				if str(a.mr_employee)+"-"+str(a.fiscal_year) not in pre_data:
					pre_data.update({str(a.mr_employee)+"-"+str(a.fiscal_year): {str(a.month):{"count": 1, "score": a.evaluator_score,"average":a.evaluator_score}}})
				else:
					if str(a.month) not in pre_data[a.mr_employee+"-"+a.fiscal_year]:
						pre_data[a.mr_employee+"-"+a.fiscal_year].update({str(a.month):{"count": 1, "score": a.evaluator_score, "average":a.evaluator_score}})
					else:
						pre_data[a.mr_employee+"-"+a.fiscal_year][a.month]["count"]   += 1
						pre_data[a.mr_employee+"-"+a.fiscal_year][a.month]["score"]   += a.evaluator_score
						pre_data[a.mr_employee+"-"+a.fiscal_year][a.month]["average"] = pre_data[a.mr_employee+"-"+a.fiscal_year][a.month]["score"]/pre_data[a.mr_employee+"-"+a.fiscal_year][a.month]["count"]
		count = 0
		# frappe.throw(str(pre_data))
		for b in pre_data:
			avg = 0.0
			c = 0
			for a in pre_data[b]:
				avg +=  pre_data[b][a]['average']
				c += 1
			avg = avg/c
			
			employee, fiscal_year = str(b).split("-")[0], str(b).split("-")[1]
			if not frappe.db.exists("Employee", {"employee": employee}):
				employee_name = frappe.db.get_value("Muster Roll Employee", employee, "person_name")
				designation = frappe.db.get_value("Muster Roll Employee", employee, "designation")
				branch = frappe.db.get_value("Muster Roll Employee", employee, "branch")
			else:
				employee_name = frappe.db.get_value("Employee", employee, "employee_name")
				designation = frappe.db.get_value("Employee", employee, "designation")
				branch = frappe.db.get_value("Employee", employee, "branch")
			data.append({
				"fiscal_year": fiscal_year,
				"employee": employee,
				"emp_name": employee_name,
				"designation": designation,
				"branch": branch,
				'average': flt(avg,2)
				})
			for c in pre_data[b]:
				month_field = get_period(int(flt(c)))
				temp = str(flt(pre_data[b][c].get('average'),2))+' ('+str(pre_data[b][c].get('count'))+')'
				data[count][scrub(month_field)] = temp 
			count+=1

	return data

def get_period(month):
	months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	period = str(months[month - 1])
	return period

def get_columns(data, filters):
	if filters.get("overall") == 1:
		columns =  [
			{"label": _("Fiscal Year"), "options": "Fiscal Year", "fieldname": "fiscal_year", "fieldtype": "Link", "width": 100},
			{"label": _("Employee ID"), "options": "Employee", "fieldname": "employee", "fieldtype": "Data", "width": 140},
			{"label": _("Employee Name"), "fieldname": "emp_name", "fieldtype": "Data", "width": 140},
			{"label": _("Designation"), "options": "Designation", "fieldname": "designation", "fieldtype": "Link", "width": 140},
			{"label": _("Branch"), "options": "Branch", "fieldname": "branch", "fieldtype": "Link", "width": 140},
		]
		for a in range(1,13):
			period = get_period(a)
			columns.append(
				{"label": _(period), "fieldname": scrub(period), "fieldtype": "Data", "width": 100}
			)
	else:
		columns =  [
			{"label": _("Fiscal Year"), "options": "Fiscal Year", "fieldname": "fiscal_year", "fieldtype": "Link", "width": 100},
			{"label": _("Evaluator ID"), "options": "Employee", "fieldname": "evaluator", "fieldtype": "Data", "width": 120},
			{"label": _("Evaluator Name"), "fieldname": "evaluator_name", "fieldtype": "Data", "width": 140},
			{"label": _("Evaluator Designation"), "options": "Designation", "fieldname": "evaluator_designation", "fieldtype": "Link", "width": 140},
			{"label": _("Employee ID"), "options": "Employee", "fieldname": "employee", "fieldtype": "Data", "width": 140},
			{"label": _("Employee Name"), "fieldname": "emp_name", "fieldtype": "Data", "width": 140},
		]
		for a in range(1,13):
			period = get_period(a)
			columns.append(
				{"label": _(period), "fieldname": scrub(period), "fieldtype": "Float", "width": 100}
			)
	
	columns += [
		{"label": _("Average %"), "fieldname": "average", "fieldtype": "Float", "width": 100},	
	]
	return columns
