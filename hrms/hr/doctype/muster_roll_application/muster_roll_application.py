# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, get_url, today

class MusterRollApplication(Document):
	def validate(self):
		self.default_validations()
	
	def on_submit(self):
		self.validate_submitter()
		self.check_status()
		self.create_mr()

	def on_cancel(self):
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
		cond = "1 = 1"
		if not self.from_project:
			frappe.throw("Select From Project Before Clicking the button")

		if self.from_project:
			cond += " and project = '{0}'".format(self.from_project)

		query = "select name as existing_cid, person_name, rate_per_day, rate_per_hour, business_activity from `tabMuster Roll Employee` where %s and status = 'Active'"

		entries = frappe.db.sql(query, cond, as_dict=True)
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
			to_date   = ""
			
			cid = i.citizenship_id if not i.is_existing else i.existing_cid
			from_date, to_date = frappe.get_value("Employee Internal Work History", {"parenttype": "Muster Roll Employee", "parent": cid, "reference_docname": self.name}, ["from_date","to_date"])

			if from_date:
				if not to_date:
					to_date = today()

				for ao in frappe.get_all("Attendance Others", fields=["name", "date"], filters={"employee_type": "Muster Roll Employee", \
						"employee": cid, "date": (">=",from_date), "date": ("<=",to_date), "status": "Present", "docstatus": ("<", 2)}):
					frappe.throw(_("Row#{0} : Unable to cancel as the employee is having attendance entries for the period from {1} till {2}.").format(i.idx, from_date, to_date), title="Dependencies found")

		frappe.delete_doc("Muster Roll Employee", frappe.db.sql_list("select name from `tabMuster Roll Employee` where reference_docname = '{0}'".format(self.name)))
		frappe.delete_doc("Employee Internal Work History", frappe.db.sql_list("select name from `tabEmployee Internal Work History` where reference_docname = '{0}'".format(self.name)))
		
	def create_mr(self):
		for a in self.items:
			if a.approver_status == 'Approved':
				cid = a.citizenship_id if not a.is_existing else a.existing_cid
				cur = frappe.db.get_value("Muster Roll Employee", cid, "name")
				if cur:
					doc = frappe.get_doc("Muster Roll Employee", cid)
					if doc.docstatus == 1 and doc.status == 'Left':
						doc.db_set("docstatus", 0)
						doc = frappe.get_doc("Muster Roll Employee", cid)

					doc.date_of_transfer = a.joining_date
				else:
					doc = frappe.new_doc("Muster Roll Employee")
					doc.joining_date = a.joining_date
					doc.reference_doctype = self.doctype
					doc.reference_docname = self.name

				doc.temp_doctype  = self.doctype
				doc.temp_docname  = self.name
				doc.person_name   = a.person_name
				doc.designation   = a.designation
				doc.bank_name     = a.bank
				doc.bank_branch   = a.bank_branch
				doc.bank_ac_no    = a.account_no
				doc.gender   	  = a.gender
				doc.qualification = a.qualification
				doc.status        = 'Active'
				doc.docstatus     = 0
				doc.branch        = self.branch
				doc.cost_center   = self.cost_center
				doc.unit          = self.unit
				doc.section       = self.section
				doc.rate_per_day  = a.rate_per_day
				doc.rate_per_hour = a.rate_per_hour
				doc.company       = self.company
				doc.id_card       = cid
				doc.business_activity = a.business_activity
				doc.bank_account_type = a.bank_account_type

				if self.project:
					doc.project = self.project

				try:
					doc.flags.ignore_permissions = 1
					doc.save()
				except Exception as e:
					frappe.throw(_('<span style="color: red;">Muster Roll Application Row#{0}: For Employee <b>{1}({2})</b></span>').format(a.idx,cid,a.person_name),title="Validation Error")

@frappe.whitelist()
def get_mr_approvers(employee):
	approver, approver_name= frappe.db.get_value("Employee", {"name":frappe.db.get_value("Employee", employee, "reports_to")}, ["user_id", "employee_name"])	
	return approver, approver_name

