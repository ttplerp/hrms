# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class EmployeeFamilyDetails(Document):
	def autoname(self):
		self.name = self.full_name+"-"+self.relationship+"-"+str(self.parent)
