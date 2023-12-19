# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, nowdate

class MusterRollApplication(Document):
	def validate(self):
		self.default_validations()
	
	def on_submit(self):
		self.validate_submitter()
		self.check_status()
		if self.from_branch and self.date_of_transfer:
			self.update_mr_master()
		else:
			self.create_mr()

	def on_cancel(self):
		if self.from_branch and self.date_of_transfer:
			self.update_mr_master(cancel=True)
		else:
			self.remove_mr()
		
	def default_validations(self):
		for i in self.items:
			if not i.joining_date:
				frappe.throw(_("Row#{0} : Date of joining is mandatory.").format(i.idx),title="Missing Value")
					
			if not i.citizenship_id and not i.existing_cid:
				frappe.throw(_("Row#{0} : Citizenship ID is mandatory.").format(i.idx),title="Missing Value")
					
			i.citizenship_id = i.citizenship_id if not i.is_existing else ""
			i.existing_cid   = i.existing_cid if i.is_existing else ""
				
	def validate_submitter(self):
		if self.approver != frappe.session.user:
			frappe.throw("Only the selected supervisor can submit this document")

	def check_status(self):
		for a in self.items:
			if not a.approver_status:
				cid = a.citizenship_id if not a.is_existing else a.existing_cid
				frappe.throw(_("Row#{0} : Approval Status cannot be empty for <b>" + str(a.person_name)+"("+str(cid) + ")</b>").format(a.idx),title="Missing Value")

	@frappe.whitelist()
	def update_requesting_info(self):
		if self.project and not self.branch:
			self.branch = frappe.db.get_value("Project", self.project, "branch")
			self.cost_center = frappe.db.get_value("Project", self.project, "cost_center")
		elif self.branch and not self.project:
			self.cost_center = frappe.db.get_value("Branch", self.branch, "cost_center")
		else:
			self.branch = frappe.db.get_value("Branch", {"cost_center": self.cost_center}, "name")
	
	@frappe.whitelist()
	def get_employees(self):
		cond = ''
		if not self.from_branch:
			frappe.throw("Select From Project Before Clicking the button")

		if self.from_branch:
			cond += " and branch = '{0}'".format(self.from_branch)
		if self.from_unit:
			cond += " and unit = '{0}'".format(self.from_unit)
		
		if self.from_branch and not self.from_unit:
			cond += " and unit IS NULL"

		query = "select name as existing_cid, person_name, gender, bank_name as bank, bank_ac_no as account_no, bank_account_type, bank_branch, rate_per_day, rate_per_hour from `tabMuster Roll Employee` where status = 'Active' {}".format(cond)

		entries = frappe.db.sql(query, as_dict=True)
		self.set('items', [])

		for d in entries:
			d.is_existing = 1
			d.joining_date = self.date_of_transfer
			row = self.append('items', {})
			row.update(d)
	
	def remove_mr(self):
		# Check for dependencies
		for i in self.items:
			from_date = ""
			to_date = ""

			cid = i.citizenship_id if not i.is_existing else i.existing_cid
			from_date, to_date = frappe.get_value("Employee Internal Work History", filters={
				"parenttype": "Muster Roll Employee",
				"parent": cid,
				"reference_docname": self.name
			}, fieldname=["from_date", "to_date"])

			if from_date:
				if not to_date:
					to_date = today()

				attendance_entries = frappe.get_all("Muster Roll Attendance", filters={
					"mr_employee": cid,
					"mr_employee_name": i.person_name,
					"date": (">=", from_date),
					"date": ("<=", to_date),
					"status": "Present",
					"docstatus": ("<", 2)
				}, fields=["name", "date"])

				if attendance_entries:
					frappe.throw(_("Row #{0}: Unable to cancel as the employee has attendance entries for the period from {1} till {2}.").format(i.idx, from_date, to_date), title="Dependencies found")

		muster_roll_employee_names = frappe.get_all("Muster Roll Employee", filters={"reference_docname": self.name}, fields=["name"])
		employee_internal_work_history_names = frappe.get_all("Employee Internal Work History", filters={"reference_docname": self.name}, fields=["name"])

		# Delete Muster Roll Employee and Employee Internal Work History documents
		frappe.delete_doc("Muster Roll Employee", muster_roll_employee_names)
		frappe.delete_doc("Employee Internal Work History", employee_internal_work_history_names)
	
	def update_mr_master(self, cancel=False):
		for a in self.items:
			if a.approver_status == 'Approved':
				doc = frappe.get_doc("Muster Roll Employee", a.existing_cid)
				doc.date_of_transfer = None if cancel else a.joining_date
				doc.branch = self.from_branch if cancel else self.branch
				doc.cost_center = frappe.db.get_value("Branch", self.from_branch, "cost_center") if cancel else self.cost_center
				doc.unit = self.from_unit if cancel else self.unit
				doc.rate_per_day = a.rate_per_day
				doc.rate_per_hour = a.rate_per_hour
				doc.designation = a.designation

			if cancel:
				frappe.db.sql("""delete from `tabEmployee Internal Work History` 
					where reference_doctype = "{}" and reference_docname = "{}"
					""".format(self.doctype, self.name))
			else:
				internal_work_history = {
					"branch": self.branch,
					"cost_center": self.cost_center,
					"from_date": a.joining_date,
					"owner": frappe.session.user,
					"creation": nowdate(),
					"modified_by": frappe.session.user,
					"modified": nowdate(),
					"reference_doctype": self.doctype,
					"reference_docname": self.name
					}
				doc.append("internal_work_history", internal_work_history)

				if self.project:
					doc.project = self.project
			try:
				doc.save(ignore_permissions=True)
			except Exception as e:
				frappe.throw(_('<span style="color: red;">Muster Roll Application Row#{0}: For Employee <b>{1}({2})</b></span>').format(a.idx, a.existing_cid, a.person_name), title="Validation Error")

	def create_mr(self):
		for a in self.items:
			if a.approver_status == 'Approved':
				try:
					doc = frappe.new_doc("Muster Roll Employee")
					doc.update({
						"joining_date": a.joining_date,
						"reference_doctype": self.doctype,
						"reference_docname": self.name,
						"temp_doctype": self.doctype,
						"temp_docname": self.name,
						"person_name": a.person_name,
						"designation": a.designation,
						"bank_name": a.bank,
						"bank_branch": a.bank_branch,
						"bank_ac_no": a.account_no,
						"gender": a.gender,
						"qualification": a.qualification,
						"status": "Active",
						"docstatus": 0,
						"branch": self.branch,
						"cost_center": self.cost_center,
						"unit": self.unit,
						"section": self.section,
						"rate_per_day": a.rate_per_day,
						"rate_per_hour": a.rate_per_hour,
						"company": self.company,
						"id_card": a.citizenship_id,
						"bank_account_type": a.bank_account_type,
					})

					if self.project:
						doc.project = self.project

					doc.flags.ignore_permissions = 1
					doc.save()
				except Exception as e:
					frappe.throw(_(
						f'<span style="color: red;">Muster Roll Application Row#{a.idx}: For Employee <b>{a.existing_cid}({a.person_name})</b></span>'),
						title="Validation Error")

@frappe.whitelist()
def get_mr_approvers(employee):
	approver, approver_name= frappe.db.get_value("Employee", {"name":frappe.db.get_value("Employee", employee, "reports_to")}, ["user_id", "employee_name"])	
	return approver, approver_name

