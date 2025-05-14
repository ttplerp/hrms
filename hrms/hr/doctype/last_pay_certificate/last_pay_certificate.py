# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class LastPayCertificate(Document):
	def validate(self):
		if not self.fixed_basic_pay or self.fixed_basic_pay < 1:
			frappe.throw("Please provide the Fixed Basic Pay")
