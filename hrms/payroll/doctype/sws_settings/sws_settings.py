# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class SWSSettings(Document):
	def validate(self):
		self.validate_plans()

	def validate_plans(self):
		immediate 	 = [i.relationship for i in self.immediate]
		nonimmediate = [i.relationship for i in self.nonimmediate]
		all 		 = immediate + nonimmediate
  
		if len(all) != len(set(all)):
			for i in self.immediate:
				for n in self.nonimmediate:
					if i.relationship == n.relationship:
						frappe.throw(_("Relationship <b>{}</b> cannot be part of both the plans").format(i.relationship))
