# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from datetime import datetime
from dateutil.relativedelta import relativedelta
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states

class SWSApplication(Document):
	def validate(self):
		validate_workflow_states(self)
		self.validate_dead()
		self.validate_amount()

				
	def validate_amount(self):
		total_amount = 0
		for a in self.items:
			if not a.amount:
				a.amount = a.claim_amount
			total_amount = flt(total_amount) + flt(a.amount)	
		self.total_amount = total_amount

	def validate_dead(self):
		for a in self.items:
			doc = frappe.get_doc("SWS Membership Item", a.reference_document)
			if doc.deceased == 1:
				frappe.throw("The dependent is marked deceased in Membership and Employee Family Detail. Please contact HR Section")

	def on_submit(self):
		if self.total_amount <= 0:
			frappe.throw("Total Amount cannot be 0 or less")
		self.update_status()
		self.post_sws_entry()
		self.create_journal_entry()
		# added by Kinley Dorji 2021/06/11
		salary_structure = frappe.get_doc("Salary Structure",{"employee":self.employee,"is_active":'Yes'})
		salary_structure.save(ignore_permissions = True)

	def update_status(self,cancel =False):
		if cancel:
			frappe.throw("Cannot Update or Cancel, This Document is Linked With Journal Entry")
		for a in self.items:
			if frappe.db.get_value("SWS Event", a.sws_event, "deceased"):
				doc = frappe.get_doc("Employee Family Details", a.reference_document)
				swsdoc = frappe.get_doc("SWS Membership Item", a.reference_document)
				if self.docstatus == 1:
					doc.db_set("deceased", 1)
					swsdoc.db_set("deceased", 1)
				if self.docstatus == 2:
					doc.db_set("deceased", 0)
					swsdoc.db_set("deceased", 0)
			row = frappe.get_doc("SWS Membership Item", a.reference_document)
			if self.docstatus == 1:
				row.status = 'Claimed'
				row.claim_amount = self.total_amount
				row.sws_application = self.name
			if self.docstatus == 2:
				row.status = 'Active'
				row.claim_amount = None
				row.sws_application = None
			row.save(ignore_permissions = True)

	def create_journal_entry(self):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1 
		cost_center = frappe.db.get_value("Branch",self.branch,"cost_center")

		je.update({
			"voucher_type": "Journal Entry",
			"company": self.company,
			"remark": self.name,
			"posting_date": self.posting_date,
			"branch": self.branch
			})

		#credit account update
		je.append("accounts", {
			"account": self.credit_account,
			"credit_in_account_currency": self.total_amount,
			"reference_type": self.doctype,
			"reference_name": self.name,
			"business_activity": "Common",
			"cost_center": cost_center
			})
		#debit account update
		je.append("accounts", {
			"account": self.debit_account,
			"debit_in_account_currency": self.total_amount,
			"reference_type": self.doctype,
			"reference_name": self.name,
			"business_activity": "Common",
			"cost_center": cost_center
			})
		
		je.save(ignore_permissions = True)
		self.db_set("je_ref", je.name)


	def post_sws_entry(self):
		doc = frappe.new_doc("SWS Entry")
		doc.flags.ignore_permissions = 1
		doc.posting_date = self.posting_date
		doc.branch = self.branch
		doc.ref_doc = self.name
		doc.company = self.company
		doc.employee = self.employee
		doc.debit = self.total_amount
		doc.submit()

	def before_cancel(self):
		self.reset_status()

	def on_cancel(self):
		self.update_status(cancel = True)
		self.delete_sws_entry()

	def reset_status(self):
		self.verified = 0
		self.approval_status = None

	def delete_sws_entry(self):
		frappe.db.sql("delete from `tabSWS Entry` where ref_doc = %s", self.name)

	@frappe.whitelist()
	def get_member_details(self, name):
		if not name:
			frappe.msgprint("Please select Reference Document first")
		relationship = cid_no = full_name = None
		data =  frappe.db.sql("""
                       select relationship, cid_no, full_name from `tabSWS Membership Item` where name = '{}'
                       """.format(name),as_dict=1)
		if len(data) > 0:
			relationship = data[0].relationship
			cid_no = data[0].cid_no
			full_name = data[0].full_name
		return relationship, cid_no, full_name

@frappe.whitelist() 
def get_event_amount(sws_event, reference, employee):
	if not reference:
		frappe.throw("Please select Reference Document")
	parent_document = frappe.db.get_value("SWS Membership Item", reference, "parent")
	registration_date = frappe.db.get_value("SWS Membership", parent_document, "registration_date")
	d1 = datetime.strptime(str(registration_date),'%Y-%m-%d')
	d2 = datetime.strptime(frappe.utils.nowdate(), '%Y-%m-%d')
	date_diff = relativedelta(d2,d1).years
	# frappe.msgprint(str(date_diff))
	if date_diff <= 1:
		event_amount = frappe.db.sql("""
                    select amount from `tabSWS Event Item` where parent = '{0}' and noof_years = 'Within 1 year'
                               """.format(sws_event), as_dict = True)
	elif date_diff > 1 and date_diff <= 2:
		event_amount = frappe.db.sql("""
                    select amount from `tabSWS Event Item` where parent = '{0}' and noof_years = 'Within 2 years'
                               """.format(sws_event), as_dict = True)
	elif date_diff > 2 and date_diff <= 3:
		event_amount = frappe.db.sql("""
                    select amount from `tabSWS Event Item` where parent = '{0}' and noof_years = 'Within 3 years'
                               """.format(sws_event), as_dict = True)
	elif date_diff > 3 and date_diff <= 4:
		event_amount = frappe.db.sql("""
                    select amount from `tabSWS Event Item` where parent = '{0}' and noof_years = 'Within 4 years'
                               """.format(sws_event), as_dict = True)
	elif date_diff >= 5:
		event_amount = frappe.db.sql("""
                    select amount from `tabSWS Event Item` where parent = '{0}' and noof_years = '5 years and above'
                               """.format(sws_event), as_dict = True)

	return event_amount

# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabSWS Application`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabSWS Application`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabSWS Application`.supervisor = '{user}' and `tabSWS Application`.workflow_state != 'Draft')
	)""".format(user=user)

