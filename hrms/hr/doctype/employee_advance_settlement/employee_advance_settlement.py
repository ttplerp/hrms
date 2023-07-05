# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt, nowdate, today, cint, get_last_day, month_diff, get_year_start, get_datetime
from frappe.utils import add_months,get_year_ending, datetime, getdate, get_first_day, math, ceil
import erpnext
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
from hrms.payroll.doctype.salary_structure.salary_structure import get_basic_and_gross_pay, get_salary_tax
from hrms.hr.utils import validate_active_employee
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from frappe.model.naming import make_autoname
from erpnext.accounts.general_ledger import (
	get_round_off_account_and_cost_center,
	make_gl_entries,
	make_reverse_gl_entries,
	merge_similar_entries,
)
from erpnext.controllers.accounts_controller import AccountsController

class EmployeeAdvanceSettlement(AccountsController):
	def validate(self):
		self.check_for_duplicate_entry()
		self.get_advance_details()
	
	def on_submit(self):
		self.validate_settlement_amounts()
		self.make_gl_entry()
		self.post_amount_to_salary_detail()
		self.update_salary_structure()
		self.update_employee_advance()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry","Payment Ledger Entry")
		self.make_gl_entry()
		self.remove_entries()
		self.update_employee_advance(cancel=1)
	
	def update_employee_advance(self, cancel=0):
		if cint(cancel) == 0:
			ea = frappe.get_doc("Employee Advance", self.employee_advance_id)
			ea.advance_settled = 1
			ea.save(ignore_permissions=True)
		else:
			ea = frappe.get_doc("Employee Advance", self.employee_advance_id)
			ea.advance_settled = 0
			ea.save(ignore_permissions=True)

	def check_for_duplicate_entry(self):
		if frappe.db.exists("Employee Advance Settlement", {"docstatus": 1, "employee_advance_id": self.employee_advance_id, "employee": self.employee}):
			frappe.throw("Advance Settlement already exists for Employee <b>{}</b> and Employee Advance <b>{}</b>".format(self.employee, self.employee_advance_id))

	def validate_settlement_amounts(self):
		settlement_amount = flt(self.settlement_amount)
		balance_amount = flt(self.balance_amount)

		if settlement_amount != balance_amount:
			frappe.throw(_("The <b>Settlement amount: '{}'</b> should be equal to the remaining <b>Outstanding amount: '{}'</b>. Partial payment is not allowed.").format(settlement_amount, balance_amount))
		elif settlement_amount < 0:
			frappe.throw(_("<b>Settlement Amount</b> amount cannot be less than zero"))
		elif not settlement_amount:
			frappe.throw(_("Please specify the <b>Settlement Amount</b>"))
	
	def make_gl_entry(self):
		gl_entries = []
		self.posting_date = self.posting_date

		debit_account = self.debit_account
		credit_account = self.advance_account
	
		if not credit_account:
			frappe.throw("Credit Account Not found")
		if not debit_account:
			frappe.throw("Debit Account not Found")

		remarks = ("Employee Advance Settlement amount received from Employee {0} dated {1}").format(self.employee, self.posting_date)
		
		gl_entries.append(
			self.get_gl_dict({
				"account": credit_account,
				"credit": self.settlement_amount,
				"credit_in_account_currency": self.settlement_amount,
				"party": self.employee,
				"party_type": "Employee",
				"against_voucher": self.name,
				"against_voucher_type": self.doctype,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"cost_center": self.cost_center,
				"business_activity": self.business_activity,
				"remarks": remarks,
			}, self.currency)
		)

		gl_entries.append(
			self.get_gl_dict({
				"account": debit_account,
				"debit": self.settlement_amount,
				"debit_in_account_currency": self.settlement_amount,
				"cost_center": self.cost_center,
				"voucher_no": self.name,
				"voucher_type": self.doctype,
				"business_activity": self.business_activity,
			}, self.currency)
		) 
				
		make_gl_entries(gl_entries, update_outstanding="No", cancel=(self.docstatus == 2), merge_entries=False)
		
	def post_amount_to_salary_detail(self):
		sd_list = []

		sd_name = make_autoname('SA-AJ.YY.MM.DD.####')
		sd_list.append((
			sd_name, str(get_datetime()), str(get_datetime()), 
			frappe.session.user, frappe.session.user, 1, self.name, 
			self.doctype, 0, flt(self.settlement_amount), flt(self.settlement_amount),
			str(self.posting_date), self.employee_advance_id
		))
	 
		if not sd_list:  
			return
		values = ', '.join(map(str, sd_list))
		frappe.db.sql("""INSERT INTO `tabSalary Detail`(name, creation, modified, 
						modified_by, owner, docstatus, parent, parenttype, idx,
						amount, default_amount, from_date, reference_number)
				VALUES {}""".format(values))                
	
	def remove_entries(self):
		frappe.db.sql("DELETE FROM `tabSalary Detail` WHERE parenttype=%s AND parent=%s", (self.doctype, self.name))
		
		ssl = frappe.get_doc('Salary Structure', {"name": self.salary_structure})
		for d in ssl.deductions:
			if d.salary_component == self.salary_component and self.employee_advance_id in (d.reference_number, d.ref_docname) and d.total_outstanding_amount == 0:
				d.total_deducted_amount -= flt(self.settlement_amount)
				d.total_outstanding_amount += flt(self.settlement_amount)
				d.to_date = None
		ssl.save(ignore_permissions=True)
	
	def update_salary_structure(self):
		ssl = frappe.get_doc('Salary Structure', {"name": self.salary_structure})
		for d in ssl.deductions:
			if d.salary_component == self.salary_component and self.employee_advance_id in (d.reference_number, d.ref_docname) and d.total_outstanding_amount > 0:
				d.update({
					"to_date": self.posting_date,
					"total_deducted_amount": flt(d.total_deducted_amount) + flt(self.settlement_amount),
					"total_outstanding_amount": flt(d.total_outstanding_amount) - flt(self.settlement_amount)
				})
		ssl.save(ignore_permissions=True)
					
	@frappe.whitelist()
	def get_advance_details(self):
		data = frappe.db.sql('''
				SELECT
					total_deductible_amount, total_deducted_amount, 
					total_outstanding_amount, reference_number, 
					salary_component
				FROM `tabSalary Detail`
				WHERE 
					parent = '{0}' 
					AND salary_component ='{1}' 
					AND total_outstanding_amount != 0 
					AND reference_number = '{2}'
		'''.format(self.salary_structure, self.salary_component, self.employee_advance_id), as_dict=1)

		for d in data:
			self.db_set("total_deducted_amount", d.total_deducted_amount)
			self.db_set("balance_amount", d.total_outstanding_amount)
			self.db_set("settlement_amount", d.total_outstanding_amount)
		
		if not data:
			frappe.throw(_("Employee <b>{}</b> does not have outstanding Advance"), title="No Advance Record")
