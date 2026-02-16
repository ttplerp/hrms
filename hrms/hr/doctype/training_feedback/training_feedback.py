# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class TrainingFeedback(Document):
	def validate(self):
		training_event = frappe.get_doc("Training Event", self.training_event)
		if training_event.docstatus != 1:
			frappe.throw(_("{0} must be submitted").format(_("Training Event")))

		emp_event_details = frappe.db.get_value(
			"Training Event Employee",
			{"parent": self.training_event, "employee": self.employee},
			["name", "attendance"],
			as_dict=True,
		)

		if not emp_event_details:
			frappe.throw(
				_("Employee {0} not found in Training Event Participants.").format(
					frappe.bold(self.employee_name)
				)
			)

		if emp_event_details.attendance == "Absent":
			frappe.throw(_("Feedback cannot be recorded for an absent Employee."))

		meta = frappe.get_meta("Training Feedback")
		field_names = [d.fieldname for d in meta.fields if d.fieldtype == "Data"]
		for field in range(len(field_names)):
			if not self.get(field_names[field]):
				frappe.throw(_("Value missing for <strong>{0}</strong>.").format(_(meta.get_label(field_names[field]))))

	def on_submit(self):
		employee = frappe.db.get_value(
			"Training Event Employee", {"parent": self.training_event, "employee": self.employee}
		)

		if employee:
			frappe.db.set_value("Training Event Employee", employee, "status", "Feedback Submitted")

	def on_cancel(self):
		employee = frappe.db.get_value(
			"Training Event Employee", {"parent": self.training_event, "employee": self.employee}
		)

		if employee:
			frappe.db.set_value("Training Event Employee", employee, "status", "Completed")


# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
    if not user: user = frappe.session.user
    user_roles = frappe.get_roles(user)
    
    if "HR User" in user_roles or "HR Manager" in user_roles:
        return

    return """(
        owner = '{user}'
        or
        exists(select 1
                from `tabEmployee`
                where `tabEmployee`.name = `tabTraining Feedback`.employee
                and `tabEmployee`.user_id = '{user}')
    )""".format(user=user)
