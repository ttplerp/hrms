# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, get_datetime
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from frappe.model.naming import make_autoname
from erpnext.accounts.general_ledger import (
	make_gl_entries,
)

from erpnext.controllers.accounts_controller import AccountsController

class EmployeeAdvanceSettlement(AccountsController):
	def validate(self):
		if self.advance_type != "Project Imprest":
			self.check_for_duplicate_entry()
			self.get_advance_details()
		if self.advance_type == "Project Imprest":
			self.get_credit_account()
			self.validate_expense_branch()
		self.calculate_amounts()
		validate_workflow_states(self)
	
	def on_submit(self):
		self.validate_settlement_amounts()
		self.make_gl_entry()
		if self.advance_type == "Salary Advance":
			self.post_amount_to_salary_detail()
			self.update_salary_structure()
			self.update_employee_advance()
	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry","Payment Ledger Entry")
		self.make_gl_entry()
		if self.advance_type == "Salary Advance":
			self.remove_entries()
			self.update_employee_advance(cancel=1)

	def validate_expense_branch(self):
		for item in self.items:
			if self.expense_branch != item.branch:
				frappe.throw("You cannot have branch <strong>{}</strong> in row #<strong>{}</strong>. Please set branch to <strong>{}</strong> or change expense branch.".format(item.branch, item.idx, self.expense_branch))
	
	def calculate_amounts(self):
		if self.advance_type == "Project Imprest":
			self.settlement_amount = 0
			for a in self.items:
				self.settlement_amount += flt(a.amount,2)
				a.tax_amount = flt(flt(a.amount,2)*(flt(self.tds_percent)/100),2)
			self.tds_amount = flt(flt(self.settlement_amount,2)*(flt(self.tds_percent)/100),2)

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

		if settlement_amount != balance_amount and self.advance_type != "Project Imprest":
			frappe.throw(_("The <b>Settlement amount: '{}'</b> should be equal to the remaining <b>Outstanding amount: '{}'</b>. Partial payment is not allowed.").format(settlement_amount, balance_amount))
		elif settlement_amount < 0:
			frappe.throw(_("<b>Settlement Amount</b> amount cannot be less than zero"))
		elif not settlement_amount:
			frappe.throw(_("Please specify the <b>Settlement Amount</b>"))

	@frappe.whitelist()
	def get_tds_account(self):
		if self.tds_percent:
			return frappe.db.get_value("TDS Account Item", {"parent": self.company, "tds_percent": self.tds_percent}, "account")
		
	@frappe.whitelist()
	def get_cost_center(self):
		return frappe.db.get_value("Branch", self.expense_branch, "cost_center")

	@frappe.whitelist()
	def get_credit_account(self):
		if self.advance_type == "Project Imprest":
			return frappe.db.get_value("Company", self.company, "imprest_advance_account")
	
	def make_gl_entry(self):
		gl_entries = []
		self.posting_date = self.posting_date

		debit_account = self.debit_account
		credit_account = self.advance_account if self.advance_type != "Project Imprest" else self.credit_account
	
		if not credit_account:
			frappe.throw("Credit Account Not found")
		if not debit_account and self.advance_type != "Project Imprest":
			frappe.throw("Debit Account not Found")

		remarks = ("Employee Advance Settlement amount received from Employee {0} dated {1}").format(self.employee, self.posting_date)
		if self.advance_type == "Project Imprest":
			gl_entries.append(
				self.get_gl_dict({
					"account": self.credit_account,
					"credit": self.settlement_amount - self.tds_amount,
					"credit_in_account_currency": self.settlement_amount - self.tds_amount,
					"party": self.employee,
					"party_type": "Employee",
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"cost_center": self.cost_center,
					"remarks": remarks,
				}, self.currency)
			)
			for b in self.items:
				gl_entries.append(
					self.get_gl_dict({
						"account": b.account,
						"debit": flt(b.amount,2),
						"debit_in_account_currency": flt(b.amount,2),
						"cost_center": b.cost_center,
						"voucher_no": self.name,
						"voucher_type": self.doctype,
						"party_type": b.party_type if frappe.db.get_value("Account", b.account, "account_type") in ("Payable", "Receivable") else "",
						"party": b.party if frappe.db.get_value("Account", b.account, "account_type") in ("Payable", "Receivable") else "",
					}, self.currency)
				)
				if flt(self.tds_percent)>0:
					gl_entries.append(
						self.get_gl_dict({
							"account": self.tds_account,
							"credit": b.tax_amount,
							"credit_in_account_currency": b.tax_amount,
							"against_voucher": self.name,
							"against_voucher_type": self.doctype,
							"voucher_type": self.doctype,
							"party": b.party,
							"party_type": b.party_type,
							"voucher_no": self.name,
							"cost_center": b.cost_center,
							"remarks": remarks,
						}, self.currency)
					)
		else:
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
		
@frappe.whitelist()
def get_expense_account(company, item):
	item_group_defaults = get_item_group_defaults(item, company)

	expense_account = item_group_defaults.expense_account
	
	if not expense_account:
		frappe.throw(
					_(
						"Please set Exepense Account either in {} or {}.".format(
							frappe.get_desk_link('Item Group', frappe.db.get_value('Item', item, 'item_group')),
							frappe.get_desk_link('Item Group', frappe.db.get_value('Item', item, 'item_sub_group')),
						)
					), 
					title=_("Expense Account Missing"),
				)
	return expense_account