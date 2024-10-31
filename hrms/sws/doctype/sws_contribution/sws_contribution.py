# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe.model.document import Document

class SWSContribution(Document):
	def validate(self):
		self.validate_duplicate_doc()
		self.calculate_total_contribution()

	def validate_duplicate_doc(self):
		if frappe.db.exists("SWS Contribution", {"employee": self.employee, "name": ["!=", self.name]}):
			frappe.throw("SWS Contribution Document for employee {} already exists. Existing Document: {}".format(self.employee, frappe.get_desk_link("SWS Contribution", frappe.db.get_value("SWS Contribution", {"employee": self.employee, "name": ["!=", self.name]}))))
		# for a in self.

	def calculate_total_contribution(self):
		total_contribution = self.opening_sws_contribution
		for cont in self.contributions:
			total_contribution += cont.contribution_amount
		self.total_contribution = flt(total_contribution,2)