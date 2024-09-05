# # -*- coding: utf-8 -*-
# # Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# # For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from datetime import datetime
from frappe.model.document import Document

class Dispatch(Document):
	def validate(self):
		self.validate_dispatch_type()

	def validate_dispatch_type(self):
		if self.dispatch_type=="In Coming":
			pass

	def before_submit(self):
		self.validate()
		self.seq_no_gen()

	def seq_no_gen(self):
		if self.dispatch_type=='Out Going':
			seq_no='0001'
		
			self.dispatch_format_det=f'{self.dispatch_format}/{datetime.now().year}/{datetime.now().month:02}/'
			result = frappe.db.sql(f"""
			SELECT max(SUBSTRING_INDEX(dispatch_number, '/', -1)) AS extracted_value
			FROM `tabDispatch`
			WHERE dispatch_number LIKE '{self.dispatch_format_det}%'
			""", as_dict=True)

			


			if result and result[0]['extracted_value'] is not None:
				output = int(result[0]['extracted_value'])+1
				seq_no=str(output).zfill(4)
			else:
				seq_no = seq_no
			
			self.dispatch_number=f'{self.dispatch_format}/{datetime.now().year}/{datetime.now().month:02}/{seq_no}'
			
	
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)
	branch=frappe.db.sql("select branch from `tabEmployee` where user_id='{user}'".format(user=user))
	
	if user == "Administrator":
		return

	if user == "Dispatch Creator":
		return

	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabDispatch`.owner = '{user}' or 
		`tabDispatch`.branch = '{branch}'
	)""".format(user=user, branch=branch[0][0])
	