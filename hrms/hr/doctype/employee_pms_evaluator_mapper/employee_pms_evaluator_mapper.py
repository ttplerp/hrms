# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class EmployeePMSEvaluatorMapper(Document):
	def validate(self):
		self.validate_duplicate()
		self.validate_self()
		self.validate_duplicate_item()
		self.update_employee_evaluators()
		self.update_mr_employee_evaluators()

	def validate_duplicate(self):
		if frappe.db.exists("""
			select name from `tabEmployee PMS Evaluator Mapper`
			where evaluator = '{}' and name != '{}'
		""".format(self.evaluator, self.name)):
			frappe.throw("Another Mapper already exists for this Evaluator")

	def on_trash(self):
		frappe.throw(_("Default Address Template cannot be deleted"))

	def validate_duplicate_item(self):
		if self.employees:
			seen = set()
			for d in self.employees:
				if d.employee in seen:
					frappe.throw(f"Duplicate entry found for Employee: <b>{d.employee}</b>")
				seen.add(d.employee)

		if self.mr_employees:
			seen = set()
			for d in self.mr_employees:
				if d.muster_roll_employee in seen:
					frappe.throw(f"Duplicate entry found for MR Employee: <b>{d.muster_roll_employee}</b>")
				seen.add(d.muster_roll_employee)

	def update_employee_evaluators(self):
		emps = [a.employee for a in self.employees]

		for a in self.employees:
			if not frappe.db.exists("Performance Evaluator", {"parent": a.employee, "evaluator": self.evaluator}):
				# max_idx = frappe.db.sql("""
				# 	SELECT MAX(idx) FROM `tabPerformance Evaluator`
				# 	WHERE parent = %s
				# """, (a.employee,))[0][0] or 0

				pe = frappe.new_doc("Performance Evaluator")
				pe.parent = a.employee
				pe.parentfield = 'evaluators'
				pe.parenttype = 'Employee'
				# pe.idx = max_idx + 1
				pe.document_type = 'Employee' if frappe.db.exists("Employee", {"name": self.evaluator}) else 'Muster Roll Employee'
				pe.evaluator = self.evaluator
				pe.evaluator_name = self.evaluator_name
				pe.insert()

		if emps:
			placeholders = ", ".join(["%s"] * len(emps))
			values = emps + [self.evaluator]

			old_evals = frappe.db.sql(f"""
				SELECT pe.name 
				FROM `tabPerformance Evaluator` pe
				JOIN `tabEmployee` e ON pe.parent = e.name
				WHERE pe.parent NOT IN ({placeholders})
				AND pe.evaluator = %s
			""", values, as_dict=True)

			for b in old_evals:
				frappe.db.delete("Performance Evaluator", {"name": b.name})
		else:
			old_evals = frappe.db.sql("""
				SELECT pe.name 
				FROM `tabPerformance Evaluator` pe
				JOIN `tabEmployee` e ON pe.parent = e.name
				WHERE pe.evaluator = %s
			""", (self.evaluator,), as_dict=True)

			for b in old_evals:
				frappe.db.delete("Performance Evaluator", {"name": b.name})

		for d in self.employees:
			doc = frappe.get_doc("Employee", d.employee)
			doc.save()

		frappe.msgprint("Updated Evaluator Information in Employees")

	def update_mr_employee_evaluators(self):
		mr_emps = []
		for a in self.mr_employees:
			mr_emps.append(a.muster_roll_employee)
			if not frappe.db.exists("Performance Evaluator", {"parent": a.muster_roll_employee, "evaluator": self.evaluator}):
				max_idx = frappe.db.sql("""
					SELECT MAX(idx) FROM `tabPerformance Evaluator` 
					WHERE parent = %s
				""", a.muster_roll_employee)[0][0] or 0

				pe = frappe.new_doc("Performance Evaluator")
				pe.parentfield='evaluators'
				pe.parenttype = 'Muster Roll Employee'
				pe.idx = max_idx + 1
				if frappe.db.exists("Employee", {"name": self.evaluator}):
					pe.document_type = 'Employee'
				else:
					pe.document_type = 'Muster Roll Employee'
				pe.evaluator = self.evaluator
				pe.evaluator_name = self.evaluator_name
				pe.parent = a.muster_roll_employee
				pe.save()

		if mr_emps:
			for b in frappe.db.sql("""
				select 
					pe.name 
				from `tabPerformance Evaluator` pe, `tabMuster Roll Employee` mre 
				where pe.parent = mre.name and
				mre.name not in ({}) and pe.evaluator = '{}'
			""".format(", ".join("'"+em+"'" for em in mr_emps), self.evaluator), as_dict=1):
				frappe.db.sql("""
					delete from `tabPerformance Evaluator` where name = '{}'
				""".format(b.name))
			frappe.msgprint("Updated Evaluator Information in Muster Roll Employees")

		if not mr_emps:
			for b in frappe.db.sql("""
				select 
					pe.name from `tabPerformance Evaluator` pe, `tabMuster Roll Employee` mre 
				where pe.parent = mre.name and pe.evaluator = '{}'
			""".format(self.evaluator), as_dict=1):
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
			emp_name = frappe.db.get_value("Employee", self.evaluator, "employee_name")
			self.evaluator_name = emp_name
		else:
			mr_employee_name = frappe.db.get_value("Muster Roll Employee", self.evaluator, "person_name")
			self.evaluator_name = mr_employee_name

	@frappe.whitelist()
	def get_employees(self):
		if not self.evaluator:
			frappe.throw("Please select Evaluator first")

		self.set("employees", [])
		for emp in frappe.db.sql("""
			select 
				name, employee_name, branch 
			from `tabEmployee` 
			where status = 'Active'
				and name != '{}'
						   
		""".format(self.evaluator),as_dict=1):
			row = self.append("employees", {})
			row.employee = emp.name
			row.employee_name = emp.employee_name
			row.branch = emp.branch

	@frappe.whitelist()
	def get_mr_employees(self):
		if not self.evaluator:
			frappe.throw("Please select Evaluator first")

		self.set("mr_employees",[])
		for emp in frappe.db.sql("""
			select 
				name, 
				person_name,
				branch 
			from `tabMuster Roll Employee` 
			where status = 'Active'
				and name != '{}' 
				and include_in_performance_evaluation = 1
		""".format(self.evaluator),as_dict=1):
			row = self.append("mr_employees", {})
			row.muster_roll_employee = emp.name
			row.muster_roll_employee_name = emp.person_name
			row.branch = emp.branch