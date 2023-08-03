# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from frappe.model.mapper import get_mapped_doc

class EmployeeTransferRequest(Document):
	def validate(self):
		validate_workflow_states(self)
		self.validate_requested_by()
		if self.workflow_state != "Approved":
			notify_workflow_states(self)

	@frappe.whitelist()
	def get_employee_details(self):
		if self.employee:
			designation =  frappe.db.get_value("Employee", self.employee, "designation")
			branch =  frappe.db.get_value("Employee", self.employee, "branch")
			employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")
			division = frappe.db.get_value("Employee", self.employee, "division")
			cell_number = frappe.db.get_value("Employee", self.employee, "cell_number")
			email = frappe.db.get_value("Employee", self.employee, "personal_email")

			return designation, branch, employee_name, division, cell_number, email

	@frappe.whitelist()
	def check_employee_transfer(self):
		created = 0
		doc = frappe.db.sql("""
			select name from `tabEmployee Transfer` where employee_transfer_request_id = '{}'
			and docstatus > 2
		""".format(str(self.name)))
		if len(doc) > 0:
			created = 1
		return created

	@frappe.whitelist()
	def validate_requested_by(self):
		if self.get("__islocal"):
			is_dept_head = 0
			current_logged_in_emp, division = frappe.db.get_value("Employee", {"user_id":frappe.session.user}, ["name","division"])
			div_head = frappe.db.get_value("Department", division, "approver")
			if not div_head:
				frappe.throw("Division Approver not set for division {} in Department Tree".format(division))
			if current_logged_in_emp != div_head:
				frappe.throw("Only Division Head {} of department {} can request for Employee Transfer".format(div_head, division))

@frappe.whitelist()
def make_employee_transfer(source_name, target_doc=None):
	def update_master(source_doc, target_doc, source_partent):
		#target_doc.project = source_doc.project
		# target_doc.invoice_title = str(target_doc.project) + "(Project Invoice)"
		# target_doc.reference_doctype = "MB Entry"
		# target_doc.reference_name	= source_doc.name
		pass

	def update_reference(source_doc, target_doc, source_parent):
			pass
			
	doclist = get_mapped_doc("Employee Transfer Request", source_name, {
		"Employee Transfer Request": {
						"doctype": "Employee Transfer",
						# "field_map":{
						# 		"project": "project",
						# 		"branch": "branch",
						# 		"customer": "customer"
						# },
						"postprocess": update_master
				},
	}, target_doc)
	return doclist		