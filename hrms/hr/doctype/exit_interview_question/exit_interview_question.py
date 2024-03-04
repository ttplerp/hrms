# -*- coding: utf-8 -*-
# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

class ExitInterviewQuestion(Document):
	def autoname(self):
		type=""
		if self.type == "Supervisor":
			type = "SPR"
		if self.type == "The Company":
			type = "CPY"
		if self.type == "Remuneration & Benefits":
			type = "R&B"
		if self.type == "Management":
			type = "MGT"
		if self.type == "Job Satisfaction":
			type = "JSF"
		name = "EXT-INT-QS-"+str(type)
		self.name = make_autoname(str(name)+".-.###")