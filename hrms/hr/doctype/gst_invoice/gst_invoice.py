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
	
	@frappe.whitelist()
	def before_submit(self):
		if not self.cbs_status or self.cbs_status != "Success":
			response, msg = gst_entry_adjustment(self.name)
			self.cbs_response = response
			self.cbs_status = msg
	
	def on_submit(self):
		pass
	
	def before_cancel(self):
		frappe.throw("Cancel is not permitted")
