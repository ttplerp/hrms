# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

class TransferRequest(Document):
	def validate(self):
		self.check_duplicate()
		self.validate_transfer_date()

		self.validate_workflow()
		self.notify_workflow()

	def check_duplicate(self):
		for t in frappe.db.get_all("Transfer Request", {"employee": self.employee, "name": ("!=", self.name), "docstatus": ("=", 0), "workflow_state": ("!=", "Rejected")}):
			frappe.throw(_("There is another transfer request {} in process").format(frappe.get_desk_link(self.doctype, t.name)), title="Duplicate Entry")		

	def validate_transfer_date(self):
		workflow_state = frappe.db.get_value("Transfer Request", self.name, "workflow_state")
		if not frappe.db.exists("Transfer Calendar",{"name": self.transfer_calendar, "start_date":("<=",nowdate()),"end_date":(">=",nowdate())}) and workflow_state in ['Draft']:
			frappe.throw(_('Transfer Request for Calendar <b>{}</b> is not open. Or its closed.').format(self.transfer_calendar))

	def validate_workflow(self):
		if self.workflow_state == "Draft":
			supervisor_id = frappe.db.get_value("Employee", self.employee, "reports_to")
			if not self.supervisor_name or not self.supervisor:
				self.supervisor_name = frappe.db.get_value("Employee", supervisor_id, "employee_name")
				self.supervisor = frappe.db.get_value("Employee", supervisor_id, "user_id")
		
		if self.workflow_state == "Rejected":
			if not self.reason_for_rejection:
				frappe.throw(_("Please provide the rejection reason"))

		if self.workflow_state == "Waiting Approval":
			if self.supervisor != frappe.session.user:
				frappe.throw(_("Only {} can take action on this request").format(self.supervisor_name))

	def notify_workflow(self):
		if self.workflow_state == "Waiting Supervisor Approval":
			parent_doc = frappe.get_doc("Transfer Request", self.name)
			args = parent_doc.as_dict()
			args.workflow_state = self.workflow_state

			email_template = frappe.get_doc("Email Template", "Transfer Request")
			message = frappe.render_template(email_template.response, args)

			sender = dict()
			doc = frappe.get_doc("User", frappe.session.user)
			sender["email"] = doc.email

			try:
				frappe.sendmail(
					recipients=[self.supervisor],
					sender=sender["email"],
					subject=email_template.subject,
					message=message
				)
			except frappe.OutgoingEmailError:
				pass

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return

	if "HR User" in user_roles or "HR Manager" in user_roles:
		return
	
	return """(
		`tabTransfer Request`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabTransfer Request`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabTransfer Request`.supervisor = '{user}' and `tabTransfer Request`.workflow_state not in ('Draft','Rejected','Cancelled'))
	)""".format(user=user)