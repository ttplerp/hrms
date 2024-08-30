# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today

class EmployeeDisciplinaryRecord(Document):
	def validate(self):
		if self.promotion_cycle:
			if not self.new_promotion_cycle:
				frappe.throw("New Promotion Cycle is Mandatory")
			if not self.new_promotion_due_date:
				frappe.throw("New Promotion Due Date is Mandatory")

	def on_submit(self):
		self.update_employee()
		self.create_disciplinary_summary()
			

	# def on_update_after_submit(self):
	# 	self.restore_on_guilty()

	def on_cancel(self):
		frappe.db.sql("delete from `tabEmployee Disciplinary Summary` where disciplinary_record = %s", (self.name))
		# if today() <= self.to_date:
		# 	emp = frappe.get_doc("Employee", self.employee)
		# 	emp.employment_status = "In Service"
		# 	if self.increment_month and self.promotion_month:
		# 		emp.increment_and_promotion_cycle = self.increment_month
		# 		emp.promotion_cycle =  self.promotion_month
		# 	else:
		# 		frappe.throw("Increment Month and Promotion months not stored previously")
		# 	emp.save()

	def restore_on_guilty(self):
		if today() <= self.to_date:
			emp = frappe.get_doc("Employee", self.employee)
			
			if self.not_guilty_or_acquitted:
				emp.employment_status = "In Service"
				if self.increment_month and self.promotion_month and self.docstatus == 1:
					emp.increment_and_promotion_cycle = self.increment_month
					emp.promotion_cycle =  self.promotion_month
				else:
					frappe.throw("Increment Month and Promotion months not stored previously")
			else:
				emp = frappe.get_doc("Employee", self.employee)
				emp.employment_status = "Suspended"
				
				increment_cycle = frappe.db.get_value("Employee", self.employee, "increment_and_promotion_cycle")
				if increment_cycle:
					emp.increment_and_promotion_cycle = ""
					
				promotion_cycle = frappe.db.get_value("Employee", self.employee, "promotion_cycle")
				if promotion_cycle:
					emp.promotion_cycle = ""
			emp.save()			

	def update_employee(self):
		pass
		# Store increment month
		# employee = frappe.get_doc("Employee", self.employee)
		# if self.salary_increment:
		# 	if not self.new_increment_month:
		# 		frappe.throw("Increment Month is Mandatory")
		# 	employee.db_set("increment_cycle", self.new_increment_month)
			# if employee.increment_cycle == "January":
			# 	employee.db_set("increment_cycle", "July")
			# elif employee.increment_cycle == "July":
			# 	employee.db_set("increment_cycle", "January")
		# Store promotion month
		# if self.promotion_cycle:
		# 	employee.db_set("promotion_cycle", self.new_promotion_cycle)
		# 	employee.db_set("promotion_due_date", self.new_promotion_due_date)
		# 	eih = frappe.db.sql("""
		# 				select name from `tabEmployee Internal Work History` where parent = '{0}' and promotion_due_date is not NULL order by idx desc limit 1
		# 			""".format(self.employee), as_dict = True)
		# 	if eih:
		# 		frappe.db.sql("""
		# 			update `tabEmployee Internal Work History` set promotion_due_date = '{}' where name = '{}'
		# 		""".format(self.new_promotion_due_date, eih[0].name))

			
		#Update Employee Master : Employment_status ="Suspended", promotion and increment cycle = blank if checked			
		# employee.employment_status = "Suspended"

		# if self.salary_increment:
		# 	emp.increment_cycle = ""

		# if self.promotion_cycle:
		# 	emp.promotion_cycle = ""

		# employee.save()
	
	def create_disciplinary_summary(self):
		emp_obj = frappe.get_doc("Employee", self.employee)
		emp_obj.flags.ignore_permissions = 1
		emp_obj.append("employee_disciplinary", {
						"from_date": self.from_date,
						"to_date": self.to_date,
						"disciplinary_action_taken": self.disciplinary_action_taken,
						"nature": self.nature,
						"complaint_frequency":self.complaint_frequency,
						"action_taken": self.action_taken,
						"remarks": self.remarks,
						# "increment_month": self.increment_month,
						# "promotion_month": self.promotion_month,
						"disciplinary_record": self.name
			})
		emp_obj.save()

# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabEmployee Disciplinary Record`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabEmployee Disciplinary Record`.employee
				and `tabEmployee`.user_id = '{user}')
	)""".format(user=user)