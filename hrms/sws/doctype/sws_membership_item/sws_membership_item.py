# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import re

class SWSMembershipItem(Document):
	def autoname(self):
		self.name = self.full_name+"-"+self.relationship+"-"+str(self.employee)
