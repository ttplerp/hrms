# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class FinancialInstitutionBranch(Document):
	def autoname(self):
		self.name = " - ".join([self.branch_name,str(self.financial_institution).strip()])
