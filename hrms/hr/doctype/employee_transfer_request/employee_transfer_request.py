# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states

class EmployeeTransferRequest(Document):
	def validate(self):
		validate_workflow_states(self)
		self.validate_requested_by()
		if self.workflow_state != "Approved":
			notify_workflow_states(self)

	@frappe.whitelist()
	def validate_requested_by(self):
		if self.get("__islocal"):
			is_dept_head = 0
			current_logged_in_emp, department = frappe.db.get_value("Employee", {"user_id":frappe.session.user}, ["name","department"])
			dept_head = frappe.db.get_value("Department", department, "approver")
			if not dept_head:
				frappe.throw("Department Approver not set for department {} in Department Tree".format(department))
			if current_logged_in_emp != dept_head:
				frappe.throw("Only Department Head {} of department {} can request for Employee Transfer".format(dept_head, department))
