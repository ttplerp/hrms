# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from datetime import date
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from erpnext.accounts.doctype.accounts_settings.accounts_settings import get_bank_account
from hrms.hr.hr_custom_functions import get_salary_tax
from hrms.hr.doctype.leave_application.leave_application \
	import get_leave_balance_on, get_leaves_for_period
import math

class EmployeeBenefits(Document):
	def validate(self):
		validate_workflow_states(self)
		if not self.employee_separation_id  and not self.employee_transfer_id and self.purpose != "Upgradation":
			frappe.throw("This document should be created through either Employee Separation or Employee Transfer")

		self.validate_gratuity()
		self.check_duplicates()
		self.validate_benefits()
		notify_workflow_states(self)
		self.set_total()

	def on_submit(self):
		if self.purpose == "Separation":
			self.update_employee()
		self.post_journal()
		self.check_leave_encashment()
		self.update_reference()

	def set_total(self):
		''' validate amounts in benefits and deductions '''
		self.total_amount = self.total_deducted_amount = self.net_amount = 0
		for e in self.items:
			e.amount, e.tax_amount, e.payable_amount = flt(e.amount,2), flt(e.tax_amount,2), flt(e.payable_amount,2)
			if flt(e.amount) < 0:
				frappe.throw(_("Row#{}: Invalid <b>Amount</b> for <b>{}</b>").format(e.idx, e.benefit_type), title="Benefit Details")
			elif flt(e.tax_amount) < 0:
				frappe.throw(_("Row#{}: Invalid <b>Tax Amount</b> for <b>{}</b>").format(e.idx, e.benefit_type), title="Benefit Details")
			elif flt(e.payable_amount) < 0:
				frappe.throw(_("Row#{}: Invalid <b>Payable Amount</b> for <b>{}</b>").format(e.idx, e.benefit_type), title="Benefit Details")

			self.total_amount 			+= flt(e.amount,2)
			self.total_deducted_amount 	+= flt(e.tax_amount,2)

		for d in self.deduction_details:
			d.amount = flt(d.amount,2)
			if flt(d.amount) < 0:
				frappe.throw(_("Row#{}: Invalid <b>Amount</b> for <b>{}</b>").format(d.idx, d.deduction_type), title="Deduction Details")
			self.total_deducted_amount += flt(d.amount)

		# if flt(self.total_deducted_amount,2) > flt(self.total_amount):
		# 	frappe.throw(_("<b>Total Deduction Amount</b> cannot be more than Total Benefits"))

		self.net_amount = flt(self.total_amount) - flt(self.total_deducted_amount)

	def check_duplicates(self):
		if self.employee_separation_id:
			for t in frappe.db.get_all("Employee Benefits", {"name": ("!=", self.name), \
					"employee_separation_id": self.employee_separation_id, "docstatus": ("!=",2)}):
				frappe.throw("Benefits for {} is already processed via {}"\
					.format(frappe.get_desk_link("Employee Separation", self.employee_separation_id), frappe.get_desk_link("Employee Benefits", t.name)))
		
		if self.employee_transfer_id:
			for t in frappe.db.get_all("Employee Benefits", {"name": ("!=", self.name), \
					"employee_transfer_id": self.employee_transfer_id, "docstatus": ("!=",2)}):
				frappe.throw("Benefits for {} is already processed via {}"\
					.format(frappe.get_desk_link("Employee Transfer", self.employee_transfer_id), frappe.get_desk_link("Employee Benefits", t.name)))

	def validate_benefits(self):
		for a in self.items:
			a.payable_amount = flt(a.amount) - flt(a.tax_amount)
			if a.benefit_type == "Leave Encashment":
				if self.purpose != "Separation" and self.purpose != "Upgradation":
					frappe.throw("Leave Encashment cannot be claimed for {}".format(self.purpose))

			if a.benefit_type != "Carriage Charges":
				a.distance = None
				a.terrain_rate = None
				a.load_capacity = None
			else:
				if not a.distance:
					frappe.throw(_("Row#{}: <b>Distance</b> for <b>Carriage Charges</b> cannot be 0").format(a.idx))
				if not a.terrain_rate:
					frappe.throw(_("Row#{}: <b>Terrain Rate</b> for <b>Carriage Charges</b> cannot be blank").format(a.idx))
				if not a.load_capacity:
					frappe.throw(_("Row#{}: <b>Load Capacity</b> for <b>Carriage Charges</b> cannot be blank").format(a.idx))

	def update_reference(self):
		if self.employee_separation_id:
			id = frappe.get_doc("Employee Separation",self.employee_separation_id)
			id.employee_benefits_status = "Claimed"
			id.save()
		elif self.employee_transfer_id:
			id = frappe.get_doc("Employee Transfer",self.employee_transfer_id)
			id.employee_benefits_status = "Claimed"
			id.save()

	def validate_gratuity(self):
		# self.total_amount = 0
		for a in self.items:
			# self.total_amount = self.total_amount + a.amount 
			if a.benefit_type=="Gratuity":
				date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")
				employee_group = frappe.db.get_value("Employee", self.employee, "employee_group")
				today_date = date.today()
				years_in_service = flt(((today_date - date_of_joining).days)/364)
				years_in_service = math.ceil(years_in_service) if (years_in_service - int(years_in_service)) >= 0.5 else math.floor(years_in_service)
				if frappe.db.get_value("Employee", self.employee, "employment_type") != "Contract":
					if years_in_service < 5:
						frappe.throw("Should have minimum of 5 years in service for Gratuity. Only <b>{0}</b> year/s in Services as of now ".format(years_in_service))
	
	def check_leave_encashment(self):
		for a in self.items:
			if a.benefit_type == "Leave Encashment":
				balance = 0
				le = frappe.get_doc("Employee Group",frappe.db.get_value("Employee",self.employee,"employee_group")) # Line added by SHIV on 2018/10/16
				las = frappe.db.sql("select name from `tabLeave Allocation` where employee = %s and leave_type = %s and to_date >= %s and YEAR(from_date) = %s and docstatus = 1", (self.employee, "Earned Leave", nowdate(), nowdate()), as_dict=True)
				if flt(a.earned_leave_balance) > flt(le.encashment_lapse):
					a.earned_leave_balance = flt(le.encashment_lapse)
				for l in las:
					if l.name != None:
						doc = frappe.get_doc("Leave Allocation", l.name)
						balance = -1*(flt(a.earned_leave_balance))
						if self.docstatus == 2:
							balance = a.earned_leave_balance
						doc.db_set("new_leaves_allocated", balance)

					self.create_additional_leave_ledger_entry(doc, balance, nowdate())

	def create_additional_leave_ledger_entry(self, allocation, leaves, date):
		''' Create leave ledger entry for leave types '''
		allocation.new_leaves_allocated = leaves
		allocation.from_date = date
		allocation.unused_leaves = 0
		allocation.create_leave_ledger_entry()

	def post_journal(self):
		emp = frappe.get_doc("Employee", self.employee)

		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		je.branch = emp.branch
		je.posting_date = self.posting_date
		je.title = str(self.purpose) + " Employee Benefits Payable (" + str(self.employee_name) + ")"
		je.voucher_type = "Journal Entry"
		je.naming_series = "Journal Voucher"
		je.remark = str(self.purpose) + 'Benefit payments for ' + str(self.employee_name) + "("+str(self.employee)+")"

		expense_bank_account = get_bank_account(self.branch)
		tax_account = frappe.db.get_value("Company", self.company, "salary_tax_account")
		
		total_amount = tax_amount = 0
		# Benefits
		for a in self.items:
			if not flt(a.amount):
				continue

			account_type = frappe.db.get_value("Account", a.gl_account, "account_type")
			party_type, party = None, None
			if account_type in ('Payable', 'Receivable'):
				party_type = "Employee"
				party = self.employee

			if a.benefit_type != "Gratuity":
				total_amount = flt(total_amount,2) + flt(a.payable_amount,2)
				je.append("accounts", {
					"account": a.gl_account,
					"reference_type": "Employee Benefits",
					"reference_name": self.name,
					"cost_center": emp.cost_center,
					"debit_in_account_currency": flt(a.amount),
					"debit": flt(a.amount),
					"party_type": party_type,
					"party": party,
					"business_activity": emp.business_activity,
				})

				if flt(a.tax_amount > 0):
					if not tax_account:
						frappe.throw("Setup Tax Account in Company")

					je.append("accounts", {
						"account": tax_account,
						"credit_in_account_currency": flt(a.tax_amount,2),
						"credit": flt(a.tax_amount,2),
						"reference_type": "Employee Benefits",
						"reference_name": self.name,
						"cost_center": emp.cost_center,
						"business_activity": emp.business_activity,
					})
					tax_amount += flt(a.tax_amount)

		# Deductions
		for b in self.deduction_details:
			if not flt(b.amount):
				continue

			account_type = frappe.db.get_value("Account", b.deduction_account, "account_type")
			party_type, party = None, None
			if account_type in ('Payable', 'Receivable'):
				party_type = "Employee"
				party = self.employee

			total_amount = flt(total_amount) - flt(b.amount,2)
			je.append("accounts", {
				"account": b.deduction_account,
				"credit_in_account_currency": flt(b.amount,2),
				"credit": flt(b.amount,2),
				"party_type": party_type,
				"party": party,
				"cost_center": emp.cost_center,
				"business_activity": emp.business_activity,
				"reference_type": "Employee Benefits",
				"reference_name": self.name,
			})

		# Credit Account
		payable_account = frappe.db.get_value("Company", self.company, "employee_payable_account")

		if flt(total_amount):
			je.append("accounts", {
				"account": payable_account,
				"cost_center": emp.cost_center,
				"credit_in_account_currency": flt(total_amount),
				"credit": flt(total_amount),
				"business_activity": emp.business_activity,
				"party_type": "Employee",
				"party": self.employee,
			})
		je.insert()
		je.submit()
		je_references = str(je.name)

		if flt(total_amount):
			jeb = frappe.new_doc("Journal Entry")
			jeb.flags.ignore_permissions = 1
			jeb.title = self.purpose+" Employee Benefits Payment(" + self.employee_name + "  " + self.name + ")"
			jeb.voucher_type = "Bank Entry"
			jeb.naming_series = "Bank Payment Voucher"
			jeb.remark = 'Benefit payment against : ' + self.name
			jeb.posting_date = self.posting_date
			jeb.branch = emp.branch
			jeb.append("accounts", {
				"account": payable_account,
				"reference_type": "Journal Entry",
				"reference_name": je.name,
				"cost_center": emp.cost_center,
				"debit_in_account_currency": flt(total_amount),
				"debit": flt(total_amount),
				"business_activity": emp.business_activity,
				"party_type": "Employee",
				"party": self.employee,
			})

			jeb.append("accounts", {
				"account": expense_bank_account,
				"cost_center": emp.cost_center,
				"reference_type": "Employee Benefits",
				"reference_name": self.name,
				"credit_in_account_currency": flt(total_amount),
				"credit": flt(total_amount),
				"business_activity": emp.business_activity,
			})
			jeb.insert()

			je_references = je_references + ", "+ str(jeb.name)

		self.db_set("journal", je_references)

	def update_employee(self):
		emp = frappe.get_doc("Employee", self.employee)
		if emp.status != "Left":
			emp.status = "Left"
			emp.employment_status = "Left"
			emp.relieving_date = self.separation_date
			emp.reason_for_resignation = self.reason_for_resignation
			history = emp.append("internal_work_history")
			history.reference_doctype = "Employee Separation"
			history.reference_docname = self.employee_separation_id
			history.from_date = self.separation_date
			emp.flags.ignore_permissions = 1
			emp.save()
			
		for a in self.items:
			doc = frappe.new_doc("Separation Benefits")
			doc.parent = self.employee
			doc.parentfield = "separation_benefits"
			doc.parenttype = "Employee"
			doc.s_b_type = a.benefit_type
			doc.s_b_currency = a.amount
			doc.save()

	def on_cancel(self):
		self.check_journal()
		self.check_leave_encashment()

	def check_journal(self):
		if self.journal:
			je = str(self.journal).split(", ")
			for a in je:
				docstatus = frappe.db.get_value("Journal Entry", a, "docstatus")
				if docstatus and docstatus != 2:
					frappe.throw("Cancel Journal Entry {0} before cancelling this document".format(frappe.get_desk_link("Journal Entry", a)))
		self.db_set("journal",None)


@frappe.whitelist()
def get_basic_salary(employee):
	amount = 0
	query = "select amount from `tabSalary Structure` s, `tabSalary Detail` d where s.name = d.parent and s.employee=\'" + str(employee) + "\' and d.salary_component in ('Basic Pay') and is_active='Yes'"
	data = frappe.db.sql(query, as_dict=True)
	if not data:
		frappe.throw("Basic Salary is not been assigned to the employee.")
	else:
		for a in data:
			amount += a.amount
	return amount

@frappe.whitelist()
def get_leave_encashment_amount(employee, date):
	basic_pay = amount = 0
	query = "select amount from `tabSalary Structure` s, `tabSalary Detail` d where s.name = d.parent and s.employee=\'" + str(employee) + "\' and d.salary_component in ('Basic Pay') and is_active='Yes'"
	data = frappe.db.sql(query, as_dict=True)
	if not data:
		frappe.throw("Basic Salary is not been assigned to the employee.")
	else:
		for a in data:
			basic_pay += a.amount
	leave_balance = get_leave_balance_on(employee, "Earned Leave", date)
	amount = (flt(basic_pay)/30.0) * flt(leave_balance)
	encashment_tax = get_salary_tax(amount)
	return amount, leave_balance, encashment_tax

@frappe.whitelist()
def get_leave_encashment_tax(amount, benefit_type):
	if benefit_type == "Leave Encashment":
		encashment_tax = get_salary_tax(amount)
		return encashment_tax

@frappe.whitelist()
def get_gratuity_amount(employee):
	basic_pay = amount = 0
	query = "select amount from `tabSalary Structure` s, `tabSalary Detail` d where s.name = d.parent and s.employee=\'" + str(employee) + "\' and d.salary_component in ('Basic Pay') and is_active='Yes'"
	data = frappe.db.sql(query, as_dict=True)
	if not data:
		frappe.throw("Basic Salary is not been assigned to the employee.")
	else:
		for a in data:
			basic_pay += a.amount
	date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
	employee_group = frappe.db.get_value("Employee", employee, "employee_group")
	today_date = date.today()
	years_in_service = flt(((today_date - date_of_joining).days)/365)
	years_in_service = math.ceil(years_in_service) if (years_in_service - int(years_in_service)) >= 0.5 else math.floor(years_in_service)
	if frappe.db.get_value("Employee", employee, "employment_type") != "Contract":
		if years_in_service < 5 and employee_group != "ESP":
			frappe.throw("Should have minimum of 5 years in service for Gratuity. Only <b>{0}</b> year/s in Services as of now ".format(years_in_service))
	elif employee_group == "ESP" and years_in_service < 1:
		frappe.throw("ESP Employee should have minimum of 1 years in service for Gratuity. Only <b>{0}</b> year/s in Services as of now ".format(years_in_service))
	if years_in_service > 0:
		amount = flt(basic_pay) * years_in_service
	return amount

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabEmployee Benefits`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabEmployee Benefits`.employee
				and `tabEmployee`.user_id = '{user}')
	)""".format(user=user)
