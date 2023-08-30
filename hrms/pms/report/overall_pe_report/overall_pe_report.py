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
	columns = get_columns(data)
	return columns, data

def get_conditions(filters):
	conditions = ''
	if filters.get("employee"):
		conditions += " and employee = %(employee)s"
	return conditions, filters

def get_data(filters):
	conditions, filters = get_conditions(filters)
	data = []
	pre_data = {}
	evaluation_data = frappe.db.sql("""
			select fiscal_year, month, evaluator, evaluator_name, employee, employee_name, designation, evaluator_score from `tabPerformance Evaluation` where docstatus = 1 %s
			"""%conditions, filters, as_dict=True)
	

	for a in evaluation_data:
		frappe.msgprint('{}'.format(a))

		if a.employee+"-"+a.fiscal_year not in pre_data:
			pre_data.update({a.employee+"-"+a.fiscal_year: [{"score":a.evaluator_score, "month":a.month}]})
		else:
			pre_data[a.employee+"-"+a.fiscal_year].append({"score":a.evaluator_score, "month":a.month})

	frappe.msgprint('{}'.format(pre_data))

	count = 0
	for b in pre_data:
		frappe.msgprint('{}'.format(b))

		avg = 0.0
		c = 0
		for a in pre_data[b]:
			frappe.msgprint('{}'.format(flt(a.get('month'))))

			avg += flt(a.get('score')) if a.get('score') else 0
			if a.get('score'): 
				c +=1
		avg = avg/c
		
		employee, fiscal_year = str(b).split("-")[0], str(b).split("-")[1]
		data.append({"fiscal_year": fiscal_year, "employee": employee, "emp_name": frappe.db.get_value("Employee", employee, "employee_name"), "designation": frappe.db.get_value("Employee", employee, "designation"), 'average': avg})
		
		for c in pre_data[b]:
			month_field = get_period(int(flt(c.get('month'))))
			data[count][scrub(month_field)]=flt(c.get('score')) if c.get('score') else 0
		count+=1

	return data

def get_period(month):
	months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	period = str(months[month - 1])
	return period

def get_columns(data):
	columns =  [
		{"label": _("Fiscal Year"), "options": "Fiscal Year", "fieldname": "fiscal_year", "fieldtype": "Link", "width": 100},
		{"label": _("Employee ID"), "options": "Employee", "fieldname": "employee", "fieldtype": "Link", "width": 140},
		{"label": _("Employee Name"), "fieldname": "emp_name", "fieldtype": "Data", "width": 140},
		{"label": _("Designation"), "options": "Designation", "fieldname": "designation", "fieldtype": "Link", "width": 140},	
	]

	for a in range(1,13):
		period = get_period(a)
		columns.append(
			{"label": _(period), "fieldname": scrub(period), "fieldtype": "Float", "width": 120}
		)
	
	columns += [
		{"label": _("Average %"), "fieldname": "average", "fieldtype": "Float", "width": 100},	
	]
	return columns