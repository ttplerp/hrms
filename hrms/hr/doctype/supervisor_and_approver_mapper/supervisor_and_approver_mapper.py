# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SupervisorAndApproverMapper(Document):
	def validate(self):
		self.check_duplicate_branch()
	
	def check_duplicate_branch(self):
		unique_items = set()
		for a in self.supervisor_items:
			if a.branch in unique_items:
				frappe.throw("Duplicate Branch <strong>{}</strong> found in supervisor list table.".format(a.branch))
			else:
				unique_items.add(a.branch)