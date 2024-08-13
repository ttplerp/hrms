# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, getdate
from frappe.model.rename_doc import rename_doc
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states

class SWSMembership(Document):
	def validate(self):
		validate_workflow_states(self)
		self.validate_duplicate_members()
		self.update_contribution()

	def update_contribution(self):
		settings 	 = frappe.get_single("SWS Settings")
		immediate 	 = [i.relationship for i in settings.immediate]
		nonimmediate = [i.relationship for i in settings.nonimmediate]
		for row in self.get("members"):
			if row.relationship not in immediate+nonimmediate:
				frappe.throw(_("Relationship <b>{}</b> is not part of any plan under <b>SWS Settings</b>").format(row.relationship))
			if row.relationship in immediate:
				if not flt(settings.cont_immediate):
					frappe.throw(_("Contribution/month for Immediate Family Members not defined under <b>SWS Settings</b>"))
				# frappe.throw(str(settings.cont_immediate))
				row.contribution = flt(settings.cont_immediate)
			elif row.relationship in nonimmediate:
				# frappe.throw(str(settings.cont_nonimmediate))
				if not flt(settings.cont_nonimmediate):
					frappe.throw(_("Contribution/month for Non-Immediate Family Members not defined under <b>SWS Settings</b>"))
				row.contribution = flt(settings.cont_nonimmediate)
				# frappe.throw(str(row.contribution))

	def update_contribution_amount(self):
		settings 	 = frappe.get_single("SWS Settings")
		immediate 	 = [i.relationship for i in settings.immediate]
		nonimmediate = [i.relationship for i in settings.nonimmediate]
		for row in self.get("members"):
			if row.relationship not in immediate+nonimmediate:
				frappe.throw(_("Relationship <b>{}</b> is not part of any plan under <b>SWS Settings</b>").format(row.relationship))

			if row.relationship in immediate:
				if not flt(settings.cont_immediate):
					frappe.throw(_("Contribution/month for Immediate Family Members not defined under <b>SWS Settings</b>"))
				# frappe.throw(str(settings.cont_immediate))
				row.contribution = flt(settings.cont_immediate)
				frappe.db.set_value("SWS Membership Item",row.name,"contribution",row.contribution)

			elif row.relationship in nonimmediate:
				# frappe.throw(str(settings.cont_nonimmediate))
				if not flt(settings.cont_nonimmediate):
					frappe.throw(_("Contribution/month for Non-Immediate Family Members not defined under <b>SWS Settings</b>"))
				row.contribution = flt(settings.cont_nonimmediate)
				frappe.db.set_value("SWS Membership Item",row.name,"contribution",row.contribution)
				# frappe.throw(str(row.contribution))
	def on_submit(self):
		self.update_employee_master_family()
		self.update_salary_structure()

	def on_cancel(self):
		self.update_employee_master_family(cancel = True)
		for a in self.members:
			frappe.db.sql("delete from `tabSWS Membership Item` where parent = '{}'".format(self.name))

	def on_update_after_submit(self):
		self.validate_duplicate_members()
		self.update_contribution_amount()
		if self.members:
			for a in self.members:
				new_name = a.full_name+"-"+a.relationship+"-"+str(self.employee)
				if new_name != a.name:
					sws = frappe.get_doc("SWS Membership Item",a.name)
					sws.save(ignore_permissions=1)
					rename_doc("SWS Membership Item", a.name, new_name, force=False, merge=False, ignore_permissions=True)
		self.update_employee_master_family()
		self.update_salary_structure()

	def validate_duplicate_members(self):
		members = []
		for a in self.members:
			members.append(a.full_name+"-"+a.relationship+"-"+self.employee)
			exists = frappe.db.sql("""
				select smi.name from `tabSWS Membership Item` smi, `tabSWS Membership` sm 
				where smi.parent = sm.name
				and smi.cid_no ='{0}'
				and smi.employee !='{1}'
				""".format(a.cid_no,self.employee))
			if exists:
				frappe.throw("CID ({}) is already registered by other employee".format(a.cid_no))

			family_details = frappe.db.sql("""
				select efd.relationship from `tabEmployee Family Details` efd, `tabEmployee` emp 
				where efd.parent = emp.name
				and emp.employee = '{0}'
				and efd.relationship = '{1}' and efd.relationship not in ('Children', 'Spouse')
				""".format(self.employee,a.relationship))
			if family_details:
				frappe.throw("Relationship ({0}) already exists in Employee Family Details of employee {1}".format(a.relationship,self.employee))				
		members_unique = set(members)
		
		if len(members) != len(members_unique):
			frappe.throw("Duplicate members with same name and same relationship")
	def update_employee_master_family(self,cancel = False):
		employee_doc = frappe.get_doc("Employee",self.employee)
		for a in self.members:
			if a.relationship == "Self":
				self_exist = frappe.db.sql("""
					select name from `tabEmployee Family Details` where parent = '{}' and relationship = "Self"
					""".format(self.employee), as_dict = 1)
				if self_exist:
					frappe.db.sql("""
						delete from `tabEmployee Family Details` where name = '{}'
						""".format(self_exist[0].name))
			exists = frappe.db.sql("""
				select name from `tabEmployee Family Details` where (parent = '{0}'
				and name = '{1}') or (parent = '{0}' and relationship = '{2}' and lower(full_name) = '{3}')
					""".format(self.employee, a.name, a.relationship, (a.full_name).lower()), as_dict=True)
			if exists:
				for d in exists:
					frappe.db.sql("""
						delete from `tabEmployee Family Details` where name = '{}'
						""".format(d.name))
			if not cancel:
				row = employee_doc.append("employee_family_details")
				row.name = a.name
				row.relationship = a.relationship
				row.full_name = a.full_name
				row.gender = a.gender
				row.dob = a.date_of_birth
				row.cid = a.cid_no
				row.dzongkhag =a.district_name
				row.gewog = a.city_name
				row.village = a.village_name
				row.cid_attach = a.cid_attach
				row.deceased = a.deceased
			else:
				frappe.msgprint("Removed {0} a {1} of Employee {2} from employee families detail".format(a.full_name,a.relationship,self.employee))
		employee_doc.save(ignore_permissions=True)

	def update_salary_structure(self):
		ss = frappe.db.sql("""
						select name from `tabSalary Structure` where is_active = 'Yes' and employee = '{}'
					""".format(self.employee),as_dict=True)
		doc = frappe.get_doc("Salary Structure", ss[0].name)

		doc.save(ignore_permissions=True)

@frappe.whitelist()
def get_sws_contribution(employee, ason_date=getdate()):
	immediate_cont 	  = 0
	nonimmediate_cont = 0

	if frappe.db.get_single_value("HR Settings", "sws_type") != "Based on Grade":
		settings = frappe.get_single("SWS Settings")
		li = frappe.db.sql("""SELECT mi.name, r.relationship_type, IFNULL(mi.contribution,0) tot_contribution
							FROM `tabSWS Membership` m, `tabSWS Membership Item` mi, `tabRelationship` r
							WHERE m.employee = "{}"
							AND m.docstatus = 1
							AND m.registration_date <= "{}"
							AND mi.parent = m.name
							AND mi.status = 'Active'
							AND r.name = mi.relationship
						""".format(employee, ason_date), as_dict=True)
		# frappe.throw(str(li))
		for i in li:
			if i.relationship_type == "Immediate":
				if settings.cont_type_immediate == "Per Head":
					immediate_cont += flt(i.tot_contribution)
				else:
					immediate_cont = flt(settings.cont_immediate)
			else:
				if settings.cont_type_nonimmediate == "Per Head":
					nonimmediate_cont += flt(i.tot_contribution)
				else:
					nonimmediate_cont = flt(settings.cont_nonimmediate)
	if settings.max_contribution:
		if immediate_cont+nonimmediate_cont <= settings.max_contribution:
			return immediate_cont+nonimmediate_cont
		else:
			return settings.max_contritubition
	else:
		return immediate_cont+nonimmediate_cont

# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles or "SWS Manager" in user_roles:
		return

	return """(
		`tabSWS Membership`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabSWS Membership`.employee
				and `tabEmployee`.user_id = '{user}')
	)""".format(user=user)