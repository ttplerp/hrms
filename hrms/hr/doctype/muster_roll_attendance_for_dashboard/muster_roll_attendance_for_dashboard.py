# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class MusterRollAttendanceforDashboard(Document):
	def validate(self):
		self.check_duplicate()
		
	def check_duplicate(self):
	
		check = frappe.db.sql('''
			SELECT 1
			FROM `tabMuster Roll Attendance for Dashboard`
			WHERE cost_center = %s AND posting_date = %s  and docstatus=1
		''', (self.cost_center, self.posting_date))

		# Throw an error if a duplicate is found
		if check:
			frappe.throw(f"Attendance already recorded for Cost Center {self.cost_center} on {self.posting_date}.")
