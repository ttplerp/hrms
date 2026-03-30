# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class GSTServiceType(Document):
	def validate(self):
		if not self.require_adjustment:
			self.service_gl_account = ''
			self.gst_gl_account = ''
	
