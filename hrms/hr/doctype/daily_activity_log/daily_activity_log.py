# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import time_diff_in_hours

class DailyActivityLog(Document):
	def validate(self):
		self.validate_duplicate()
		self.validate_overlapping_time()

	def validate_duplicate(self):
		if frappe.db.exists("Daily Activity Log", {"employee": self.employee, "posting_date": self.posting_date, "name": ["!=", self.name], "docstatus": ["<", 2], "name": ["!=", self.name]}):
			frappe.throw("There already exists Daily Activity Log for employee {0} on posting date {1}. Existing Daily Activity Log: <b><a href='/app/daily-activity-log/{2}'>{2}</a></b>".format(self.employee, self.posting_date, frappe.db.get_value("Daily Activity Log", {"employee": self.employee, "posting_date": self.posting_date, "docstatus": ["<", 2], "name": ["!=", self.name]})))

	def validate_overlapping_time(self):
		for a in self.activities:
			if not a.start_time or not a.end_time:
				frappe.throw(_("Row#{} : Start Time or End Time cannot be blank").format(a.idx), title="Invalid Input")
			else:
				pass
			for b in self.activities:
				if (a.start_time >= b.start_time and a.start_time <= b.end_time) and a.idx != b.idx:
					frappe.throw(_("Row#{}: Start Time is overlapping with Row#{}").format(a.idx, b.idx))
				elif (a.end_time >= b.start_time and a.end_time <= b.end_time) and a.idx != b.idx:
					frappe.throw(_("Row#{}: End Time is overlapping with Row#{}").format(a.idx, b.idx))

	@frappe.whitelist()
	def calculate_duration(self, start_time, end_time):
		if start_time and end_time:
			return time_diff_in_hours(end_time, start_time)

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabDaily Activity Log`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabDaily Activity Log`.employee
				and `tabEmployee`.user_id = '{user}'))
    """.format(user=user)
			
