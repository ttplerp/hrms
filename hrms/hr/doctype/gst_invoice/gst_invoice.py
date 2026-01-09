# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.integrations.bank_api import gst_entry_adjustment

class GSTInvoice(Document):
	def validate(self):
		if not self.item:
			frappe.throw("Please enter GST Item")
	
	def before_submit(self):
		response, msg = gst_entry_adjustment(self.name)
		self.cbs_response = response
		self.cbs_status = msg
	
	def on_submit(self):
		pass
	
	def before_cancel(self):
		frappe.throw("Cancel is not permitted")

	@frappe.whitelist()
	def make_cbs_entry(self):
		if not self.cbs_response or self.cbs_response != "SUCCESS":
			response, msg = gst_entry_adjustment(self.name)
			# self.cbs_response = response
			# self.cbs_status = msg
			frappe.db.set_value(self.doctype, self.name, {
				'cbs_response': response,
				'cbs_status': msg
			}, update_modified=True)
