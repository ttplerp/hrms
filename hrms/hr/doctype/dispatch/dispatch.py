# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Dispatch(Document):
	def validate(self):
		self.validation()
		self.generate_document_no()
	
	def validation(self):
		if self.dispatch_type in ("Incoming","Out-Going"):
			if not self.date:
				frappe.throw("Date and Subject is required!")

	def generate_document_no(self):
		if self.dispatch_type == "Out-Going":
			if self.dispatch_format:
				if frappe.db.exists({
					'doctype': 'Dispatch',
					'dispatch_format': self.dispatch_format}):
					for a in frappe.db.sql(
							"""
								SELECT 
									MAX(dispatch_serial_no) as max_sl_no 
								FROM `tabDispatch` 
								WHERE dispatch_format = '{}' 
								AND docstatus > 0 AND docstatus < 2
							""".format(self.dispatch_format), as_dict=1):
					
						if a.max_sl_no is None:
							a.max_sl_no = 0
							sl_no = a.max_sl_no + 1
						else:
							sl_no = a.max_sl_no + 1
				else:
					sl_no = 1
				self.dispatch_serial_no = sl_no
				self.dispatch_no = str(self.dispatch_format) + str(sl_no)
			else:
				frappe.throw("Please select Dispatch Format")
