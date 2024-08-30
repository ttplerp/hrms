# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import time_diff_in_seconds
from frappe.model.mapper import get_mapped_doc

from erpnext.setup.doctype.employee.employee import get_employee_emails


class TrainingEvent(Document):
	def validate(self):
		self.set_employee_emails()
		self.validate_period()

	def on_update_after_submit(self):
		self.set_status_for_attendees()

	def set_employee_emails(self):
		self.employee_emails = ", ".join(get_employee_emails([d.employee for d in self.employees]))

	def validate_period(self):
		if time_diff_in_seconds(self.end_time, self.start_time) <= 0:
			frappe.throw(_("End time cannot be before start time"))

	def set_status_for_attendees(self):
		if self.event_status == "Completed":
			for employee in self.employees:
				if employee.attendance == "Present" and employee.status != "Feedback Submitted":
					employee.status = "Completed"

		elif self.event_status == "Scheduled":
			for employee in self.employees:
				employee.status = "Open"

		self.db_update_all()

@frappe.whitelist()
def create_travel_request(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.employee = frappe.flags.args.get("employee")
		target.employee_name = frappe.db.get_value("Employee", target.employee, "employee_name")
		target.designation = frappe.db.get_value("Employee", target.employee, "designation")
		target.grade = frappe.db.get_value("Employee", target.employee, "grade")
		target.cell_number = frappe.db.get_value("Employee", target.employee, "cell_number")
		target.prefered_email = frappe.db.get_value("Employee", target.employee, "company_email")
		target.travel_type = source.international_or_domestic
		target.training_event = source.name
		target.training_event_child_ref = frappe.flags.args.get("child_ref")

	doc = get_mapped_doc("Training Event", source_name, {
			"Training Event": {
				"doctype": "Travel Request",
				"field_map": {
					"name": "transaction_no",
				}},
	}, target_doc, set_missing_values, ignore_permissions=True)
	return doc
