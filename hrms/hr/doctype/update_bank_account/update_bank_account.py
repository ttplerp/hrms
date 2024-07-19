# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class UpdateBankAccount(Document):
	def validate(self):
		self.validate_desuup()

	def validate_desuup(self):
		if self.did:
			doc=frappe.get_doc("Desuup", self.did)
			if self.cid_number != doc.cid_number or self.date_of_birth != doc.date_of_birth:
				frappe.throw("<b> {} </b> : Desuup Details like DOB and CID don't match with record maintained in ERP ".format(self.did))
			else:
				if self.bank_name and self.bank_account_number and self.bank_account_type:
					doc.bank_name = self.bank_name if self.bank_name else doc.bank_name
					doc.bank_branch = self.bank_branch if self.bank_branch else doc.bank_branch
					doc.bank_account_type = self.bank_account_type if self.bank_account_type else doc.bank_account_type
					doc.bank_account_number = self.bank_account_number if self.bank_account_number else doc.bank_account_number
					doc.email_id = self.email_id if self.email_id else doc.email_id
					doc.mobile_number = self.mobile_number if self.mobile_number else doc.mobile_number
					doc.save()
				else:
					frappe.throw("Bank Details are missing")

@frappe.whitelist(allow_guest=True)
def get_detail(did, cid, dob):
	if frappe.db.exists("Desuup", did):
		doc=frappe.get_doc("Desuup", did)
		if cid == doc.cid_number and dob == doc.date_of_birth:
			return doc

			



