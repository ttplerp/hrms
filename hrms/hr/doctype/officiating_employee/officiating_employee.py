# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate
from frappe.utils.data import add_days

class OfficiatingEmployee(Document):
	def validate(self):
		if self.employee == self.officiate:
			frappe.throw("Both Employee and Officiating Employee can not be same person")

	def on_submit(self):
		user = frappe.get_doc("User", frappe.db.get_value("Employee", self.officiate, "user_id"))
		user.flags.ignore_permissions = True

		roles = [i.role for i in user.roles]
		if "Leave Approver" not in roles:
			user.add_roles("Leave Approver")
			self.db_set("already", 0)
		else:
			self.db_set("already", 1)
		
		if len(self.roles) > 0:
			for a in self.roles:
				if str(a.role) not in roles:
					user.add_roles(str(a.role))

	@frappe.whitelist()
	def get_roles(self):
		if self.employee and not frappe.db.get_value("Employee",self.employee,"user_id"):
			frappe.throw("No User found for Employee {}".format(self.employee))
		if self.officiate and not frappe.db.get_value("Employee",self.officiate,"user_id"):
			frappe.throw("No User found for Employee {}".format(self.officiate))
		roles = frappe.get_roles(frappe.db.get_value("Employee",self.employee,"user_id"))
		o_roles = frappe.get_roles(frappe.db.get_value("Employee",self.officiate,"user_id")) 
		if roles:
			self.set("roles",[])
			for a in roles:
				if a not in o_roles:
					row = self.append("roles",{})
					a = {'role':a}
					row.update(a)
	
	@frappe.whitelist()
	def revoke_perm(self):
		if self.revoked:
			frappe.throw("Already Revoked")
		if getdate(self.to_date) > getdate(nowdate()):
			self.db_set("to_date", nowdate())

		self.db_set("revoked", 1)
		if len(self.roles) > 0:
			user = frappe.get_doc("User", frappe.db.get_value("Employee", self.officiate, "user_id"))
			user.flags.ignore_permissions = True
			for a in self.roles:
				user.remove_roles(str(a.role))			

		frappe.msgprint("Permissions Revoked")

def check_off_exp():
	off = frappe.db.sql("""select name from `tabOfficiating Employee` 
		where docstatus = 1 and to_date = %(today)s""", {"today": add_days(nowdate(), -1)}, as_dict=True)
	for a in off:
		print(str(a))
		doc = frappe.get_doc("Officiating Employee", a)
		doc.revoke_perm()
