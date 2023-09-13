# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class EmployeePMSEvaluatorMapper(Document):
	def validate(self):
		self.validate_duplicate()
		self.validate_self()
		self.update_employee_evaluators()
		self.update_mr_employee_evaluators()

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

	def update_mr_employee_evaluators(self):
		mr_emps = []
		for a in self.mr_employees:
			mr_emps.append(a.muster_roll_employee)
			if not frappe.db.exists("Performance Evaluator", {"parent": a.muster_roll_employee, "evaluator": self.evaluator}):
				pe = frappe.new_doc("Performance Evaluator")
				pe.parentfield='evaluators'
				pe.parenttype = 'Muster Roll Employee'
				pe.evaluator = self.evaluator
				pe.evaluator_name = self.evaluator_name
				pe.parent = a.muster_roll_employee
				pe.insert()
		for b in frappe.db.sql("""
			select pe.name from `tabPerformance Evaluator` pe, `tabMuster Roll Employee` mre where pe.parent = mre.name and
			mre.name not in ({}) and pe.evaluator = '{}'
		""".format(", ".join("'"+em+"'" for em in mr_emps), self.evaluator), as_dict=1):
			frappe.db.sql("""
				delete from `tabPerformance Evaluator` where name = '{}'
			""".format(b.name))
		frappe.msgprint("Updated Evaluator Information in Muster Roll Employees")


	def validate_self(self):
		for a in self.employees:
			if self.evaluator == a.employee:
				frappe.throw("Evaluator has himself/herself in Employees Table")

	@frappe.whitelist()
	def get_employee_name(self):
		if self.document_type == "Employee":
			employee_name = frappe.db.get_value("Employee", self.evaluator, "employee_name")
			self.evaluator_name = employee_name
		else:
			mr_employee_name = frappe.db.get_value("Muster Roll Employee", self.evaluator, "person_name")
			self.evaluator_name = mr_employee_name

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

	@frappe.whitelist()
	def get_mr_employees(self):
		if not self.evaluator:
			frappe.throw("Please select Evaluator first")
		self.set("mr_employees",[])
		for emp in frappe.db.sql("""
			select name, person_name from `tabMuster Roll Employee` where status = 'Active'
			and name != '{}'
		""".format(self.evaluator),as_dict=1):
			row = self.append("mr_employees", {})
			row.muster_roll_employee = emp.name
			row.muster_roll_employee_name = emp.person_name

		
