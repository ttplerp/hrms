# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe import _
import frappe
from frappe.utils import flt
from frappe.model.document import Document

class BatchDataCommunication(Document):
	def validate(self):
		self.validate_existing()
        
	def on_submit(self):
		self.submit_bdc()

	def validate_existing(self):
		doc = []
		doc = frappe.db.sql("""
            select name from `tabBatch Data Communication` where ((from_date between '{0}' and '{1}') or (to_date between '{0}' and '{1}')) and name != '{2}' and branch = '{3}' and docstatus != 2
                      """.format(self.from_date,self.to_date, self.name, self.branch),as_dict=True)
		if doc != [] and doc != None and doc != "":
			frappe.throw("BDC for branch {3}, from date {0} and to date {1} already exists.".format(self.from_date, self.to_date, self.name, self.branch,))

	@frappe.whitelist()
	def get_employees(self, branch = None):
		data = []
		self.set("employees", [])
		if branch:
			employee_list = frappe.db.sql("""
				select a.name as employee, a.employee_name
				from `tabEmployee` a
				where a.branch = '{}' and a.status = 'Active'
			""".format(branch),as_dict=True)
		else:
			employee_list = frappe.db.sql("""
				select a.name as employee, a.employee_name
				from `tabEmployee` a
				where a.status = 'Active'
			""",as_dict=True)
		if employee_list:
			for a in employee_list:
				row = self.append("employees", {})
				row.update(a)
		# return data

	def submit_bdc(self):
		field_name = ""
		field_name = frappe.db.get_value("Salary Component",self.salary_component,"field_name")
		self.remove_salary_structure_components(field_name)
		self.update_salary_structure(field_name)

	# def get_house_rent_rate(self, place, town):
	# 	return frappe.db.get_value("House Rent Deduction Details",{"parent":place,"town":town},"rate")


	def remove_salary_structure_components(self, field_name):
		ss_list = frappe.db.sql("""
            select name from `tabSalary Structure` where is_active = 'Yes' and {} = 1 and employee in (select e.name from `tabEmployee` e where e.branch = '{}')
        """.format(field_name, self.branch), as_dict = True)
		if ss_list:
			if len(ss_list) > 100:
				frappe.enqueue(remove_ss_component, timeout=600, promotion_entry=self, employee_promotions=ep_list)
			else:
				remove_ss_component(ss_list, self.salary_component, field_name)

	def update_salary_structure(self, field_name):
		for a in self.employees:
			ss = frappe.db.sql("""
						select name from `tabSalary Structure` where is_active = 'Yes' and employee = '{}'
						""".format(a.employee),as_dict=True)
			doc = frappe.get_doc("Salary Structure",ss[0].name)

			if a.amount > 0.0:
				doc.db_set(field_name,1)
				if frappe.db.get_value("Salary Component", self.salary_component, "type") == "Deduction":
					row = doc.append("deductions",{})
				if frappe.db.get_value("Salary Component", self.salary_component, "type") == "Earning":
					row = doc.append("earnings",{})
				row.amount = a.amount
				row.salary_component = self.salary_component
				row.from_date = self.from_date
				row.to_date = self.to_date

			doc.save(ignore_permissions=True)
			
def remove_ss_component(ss_list, salary_component, field_name, publish_progress = False):
	count = 0
	n = len(ss_list)
	frappe.publish_realtime("progress", dict(progress=[count+1, n],title=("Removing Components from previous eligible employees.")),user=frappe.session.user)
	for b in ss_list:
		count += 1
		doc = frappe.get_doc("Salary Structure", b.name)
		doc.db_set(field_name,0)
		doc.save(ignore_permissions=True)
	frappe.msgprint(("{0} Previous Component Eligibility Removed").format(n), title=_("Success"), indicator="green")

# Following code added by SHIV on 2021/05/13
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "System Manager" in user_roles: 
		return

	return """(
		exists(select 1
			from `tabEmployee` as e
			where e.branch = `tabBatch Data Communication`.branch
			and e.user_id = '{user}')
		or
		exists(select 1
			from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
			where e.user_id = '{user}'
			and ab.employee = e.name
			and bi.parent = ab.name
			and bi.branch = `tabBatch Data Communication`.branch)
	)""".format(user=user)
