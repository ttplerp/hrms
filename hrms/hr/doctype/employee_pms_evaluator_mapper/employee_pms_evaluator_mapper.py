# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class EmployeePMSEvaluatorMapper(Document):
	def validate(self):
		self.validate_duplicate()
		self.validate_self()
		self.update_employee_evaluators()

	def validate_duplicate(self):
		if frappe.db.exists("""
			select name from `tabEmployee PMS Evaluator Mapper`
			where evaluator = '{}' and name != '{}'
		""".format(self.evaluator, self.name)):
			frappe.throw("Another Mapper already exists for this Evaluator")

	def update_employee_evaluators(self):
		emps = []
		for a in self.employees:
			emps.append(a.employee)
			if not frappe.db.exists("Performance Evaluator", {"parent": a.employee, "evaluator": self.evaluator}):
				pe = frappe.new_doc("Performance Evaluator")
				pe.parentfield='evaluators'
				pe.parenttype = 'Employee'
				pe.evaluator = self.evaluator
				pe.evaluator_name = self.evaluator_name
				pe.parent = a.employee
				pe.insert()
		for b in frappe.db.sql("""
			select pe.name from `tabPerformance Evaluator` pe, `tabEmployee` e where pe.parent = e.name and
			e.name not in ({}) and pe.evaluator = '{}'
		""".format(", ".join("'"+em+"'" for em in emps), self.evaluator), as_dict=1):
			frappe.db.sql("""
				delete from `tabPerformance Evaluator` where name = '{}'
			""".format(b.name))
		frappe.msgprint("Updated Evaluator Information in Employees")


	def validate_self(self):
		for a in self.employees:
			if self.evaluator == a.employee:
				frappe.throw("Evaluator has himself/herself in Employees Table")


	@frappe.whitelist()
	def get_employees(self):
		if not self.evaluator:
			frappe.throw("Please select Evaluator first")
		self.set("employees",[])
		for emp in frappe.db.sql("""
			select name, employee_name from `tabEmployee` where status = 'Active'
			and name != '{}'
		""".format(self.evaluator),as_dict=1):
			row = self.append("employees", {})
			row.employee = emp.name
			row.employee_name = emp.employee_name		
