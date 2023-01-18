# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Notesheet(Document):
	def validate(self):
		self.validation()

	def validation(self):
		if self.workflow_state == "Waiting Approval":
			if self.owner != frappe.session.user:
				frappe.throw("Only the creator of this notesheet can Apply!")
		
		if self.workflow_state in ("Approved", "Rejected"):
			approver = frappe.db.get_value("HR Settings", "notesheet_approver_name", "notesheet_approver_name")
			if frappe.db.get_value("Employee", {"user_id":frappe.session.user}, "name") != frappe.db.get_value("HR Settings", "notesheet_approver", "notesheet_approver"):
				frappe.throw("Only <b>{}</b> can Approve/Reject this request".format(approver))
			
			self.approver = approver

  