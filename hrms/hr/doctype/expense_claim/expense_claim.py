# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, flt, get_link_to_form, today

import erpnext
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.controllers.accounts_controller import AccountsController

from hrms.hr.utils import set_employee_name, share_doc_with_approver, validate_active_employee


class InvalidExpenseApproverError(frappe.ValidationError):
	pass

class ExpenseApproverIdentityError(frappe.ValidationError):
	pass


class ExpenseClaim(AccountsController):
	def onload(self):
		self.get("__onload").make_payment_via_journal_entry = frappe.db.get_single_value(
			"Accounts Settings", "make_payment_via_journal_entry"
		)

	def validate(self):
		validate_active_employee(self.employee)
		set_employee_name(self)

		self.validate_references()
		self.validate_sanctioned_amount()
		self.calculate_total_amount()
		self.validate_advances()
		self.set_expense_account(validate=True)
		self.set_payable_account()
		self.set_cost_center()
		self.calculate_taxes()
		self.set_status()
		# self.calculate_grand_total()
		if self.task and not self.project:
			self.project = frappe.db.get_value("Task", self.task, "project")
		
		self.validate_amount()

	def validate_amount(self):
		if flt(self.total_sanctioned_amount) == 0:
			fr
		
		pass

	def validate_references(self):
		for a in self.expenses:
			if a.expense_type in ('Leave Encashment','Travel','Meeting & Seminars','Training') and not a.reference:
				frappe.throw("Cannot create Expense Claim for {} directly from Expense Claim.".format(a.expense_type),title="Invalid Operation")

	def set_status(self, update=False):
		status = {"0": "Draft", "1": "Submitted", "2": "Cancelled"}[cstr(self.docstatus or 0)]

		precision = self.precision("grand_total")

		if (
			# set as paid
			self.is_paid
			or (
				flt(self.total_sanctioned_amount > 0)
				and (
					# grand total is reimbursed
					(
						self.docstatus == 1
						and flt(self.grand_total, precision) == flt(self.total_amount_reimbursed, precision)
					)
					# grand total (to be paid) is 0 since linked advances already cover the claimed amount
					or (flt(self.grand_total, precision) == 0)
				)
			)
		) and self.approval_status == "Approved":
			status = "Paid"
		elif (
			flt(self.total_sanctioned_amount) > 0
			and self.docstatus == 1
			and self.approval_status == "Approved"
		):
			status = "Unpaid"
		elif self.docstatus == 1 and self.approval_status == "Rejected":
			status = "Rejected"

		if update:
			self.db_set("status", status)
		else:
			self.status = status

	# def calculate_grand_total(self):
	# 	self.grand_total = flt(self.total_sanctioned_amount) + flt(self.total_taxes_and_charges) - flt(self.total_advance_amount)
		
	def on_update(self):
		share_doc_with_approver(self, self.expense_approver)

	def set_payable_account(self):
		if not self.payable_account and not self.is_paid:
			self.payable_account = frappe.get_cached_value(
				"Company", self.company, "default_expense_claim_payable_account"
			)

	def set_cost_center(self):
		if not self.cost_center:
			self.cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

	def on_submit(self):
		# commented as approver not required
		# if self.approval_status == "Draft":
		# 	frappe.throw(_("""Approval Status must be 'Approved' or 'Rejected'"""))

		self.update_task_and_project()
		self.make_gl_entries()
		self.post_accounts_entry()
		if self.is_paid:
			update_reimbursed_amount(self, self.grand_total)

		self.set_status(update=True)
		self.update_claimed_amount_in_employee_advance()
		self.set_travel_reference()
	def before_cancel(self):
		for a in self.expenses:
			if a.reference_type == 'Leave Encashment':
				frappe.db.sql("""
					update `tabLeave Encashment` set expense_claim = NULL where name = '{}'
				""".format(a.reference))

	def on_cancel(self):
		self.update_task_and_project()
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")
		if self.payable_account:
			self.make_gl_entries(cancel=True)

		if self.is_paid:
			update_reimbursed_amount(self, -1 * self.grand_total)

		self.update_claimed_amount_in_employee_advance()
		self.set_travel_reference(cancel = True)

	# Following method added by SHIV on 2020/10/02
	def post_accounts_entry(self):
		if not self.cost_center:
			frappe.throw("Setup Cost Center for employee in Employee Information")

		expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		if not expense_bank_account:
			expense_bank_account = frappe.db.get_single_value("Company", self.company, "default_bank_account")
			if not expense_bank_account:
				frappe.throw("Setup Expense Bank Account in Branch or Default Expense Bank Account in Company Accounts Settings")

		# expense_account = frappe.db.get_value("Company", self.company, "leave_encashment_account")
		employee_payable_account = frappe.db.get_value("Company", self.company, "employee_payable_account")
		# if not expense_account:
		# 	frappe.throw("Setup Leave Encashment Account in Company Settings")

		# tax_account = frappe.db.get_value("Company", self.company, "salary_tax_account")
		# if not tax_account:
		# 	frappe.throw("Setup Tax Account in Company Settings")

		#Payment Journal Entry
		if flt(self.total_claimed_amount) > 0:
			jeb = frappe.new_doc("Journal Entry")
			jeb.flags.ignore_permissions = 1
			jeb.title = "Expsense Claim Payment(" + self.employee_name + "  " + self.name + ")"
			jeb.voucher_type = "Bank Entry"
			jeb.naming_series = "ACC-JV-.YYYY.-"
			expense_claim_type = ""
			for b in self.expenses:
				expense_claim_type = b.expense_type
			jeb.remark = 'Payment against Expense Claim('+expense_claim_type+') : ' + self.name
			jeb.user_remark = 'Payment against Expense Claim('+expense_claim_type+') : ' + self.name
			jeb.posting_date = today()
			jeb.branch = self.branch
			jeb_cost_center = frappe.db.get_value("Branch", jeb.branch, "cost_center")
			jeb.append("accounts", {
					"account": employee_payable_account,
					"reference_type": "Expense Claim",
					"reference_name": self.name,
					"cost_center": self.cost_center,
					"debit_in_account_currency": self.grand_total,
					"debit": self.grand_total,
					"business_activity": "Common",
					"party_type": "Employee",
					"user_remark": 'Payment against Expense Claim('+expense_claim_type+') : ' + self.name,
					"party": self.employee
				})
			jeb.append("accounts", {
					"account": expense_bank_account,
					"cost_center": self.cost_center,
					"reference_type": "Expense Claim",
					"reference_name": self.name,
					"credit_in_account_currency": self.grand_total,
					"credit": self.grand_total,
					"user_remark": 'Payment against Expense Claim('+expense_claim_type+') : ' + self.name,
					"business_activity": "Common",
				})
			jeb.insert()

			payment_journal = str(jeb.name)

		self.db_set("payment_journal", payment_journal)
		frappe.db.commit()

	def update_claimed_amount_in_employee_advance(self):
		for d in self.get("advances"):
			frappe.get_doc("Employee Advance", d.employee_advance).update_claimed_amount()

	def update_task_and_project(self):
		if self.task:
			task = frappe.get_doc("Task", self.task)

			ExpenseClaim = frappe.qb.DocType("Expense Claim")
			task.total_expense_claim = (
				frappe.qb.from_(ExpenseClaim)
				.select(Sum(ExpenseClaim.total_sanctioned_amount))
				.where(
					(ExpenseClaim.docstatus == 1)
					& (ExpenseClaim.project == self.project)
					& (ExpenseClaim.task == self.task)
				)
			).run()[0][0]

			task.save()
		elif self.project:
			frappe.get_doc("Project", self.project).update_project()

	def make_gl_entries(self, cancel=False):
		if flt(self.total_sanctioned_amount) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		gl_entry = []
		self.validate_account_details()

		# payable entry
		if self.grand_total:
			gl_entry.append(
				self.get_gl_dict(
					{
						"account": self.payable_account,
						"credit": self.grand_total,
						"credit_in_account_currency": self.grand_total,
						"against": ",".join([d.default_account for d in self.expenses]),
						"party_type": "Employee",
						"party": self.employee,
						"against_voucher_type": self.doctype,
						"against_voucher": self.name,
						"cost_center": self.cost_center,
					},
					item=self,
				)
			)
		# frappe.throw(str(gl_entry))
		# expense entries
		for data in self.expenses:
			gl_entry.append(
				self.get_gl_dict(
					{
						"account": data.default_account,
						"debit": data.sanctioned_amount,
						"debit_in_account_currency": data.sanctioned_amount,
						"against": self.employee,
						"cost_center": data.cost_center or self.cost_center,
					},
					item=data,
				)
			)
		for data in self.advances:
			gl_entry.append(
				self.get_gl_dict(
					{
						"account": data.advance_account,
						"credit": data.allocated_amount,
						"credit_in_account_currency": data.allocated_amount,
						"against": ",".join([d.default_account for d in self.expenses]),
						"party_type": "Employee",
						"party": self.employee,
						"against_voucher_type": "Employee Advance",
						"against_voucher": data.employee_advance,
					}
				)
			)

		self.add_tax_gl_entries(gl_entry)

		if self.is_paid and self.grand_total:
			# payment entry
			payment_account = get_bank_cash_account(self.mode_of_payment, self.company).get("account")
			gl_entry.append(
				self.get_gl_dict(
					{
						"account": payment_account,
						"credit": self.grand_total,
						"credit_in_account_currency": self.grand_total,
						"against": self.employee,
					},
					item=self,
				)
			)

			gl_entry.append(
				self.get_gl_dict(
					{
						"account": self.payable_account,
						"party_type": "Employee",
						"party": self.employee,
						"against": payment_account,
						"debit": self.grand_total,
						"debit_in_account_currency": self.grand_total,
						"against_voucher": self.name,
						"against_voucher_type": self.doctype,
					},
					item=self,
				)
			)

		return gl_entry

	def add_tax_gl_entries(self, gl_entries):
		# tax table gl entries
		for tax in self.get("taxes"):
			# commented coz we need to credit the tax amount
			# gl_entries.append(
			# 	self.get_gl_dict(
			# 		{
			# 			"account": tax.account_head,
			# 			"debit": tax.tax_amount,
			# 			"debit_in_account_currency": tax.tax_amount,
			# 			"against": self.employee,
			# 			"cost_center": self.cost_center,
			# 			"against_voucher_type": self.doctype,
			# 			"against_voucher": self.name,
			# 		},
			# 		item=tax,
			# 	)
			# )
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": tax.account_head,
						"credit": tax.tax_amount,
						"credit_in_account_currency": tax.tax_amount,
						"against": self.employee,
						"cost_center": self.cost_center,
						"against_voucher_type": self.doctype,
						"against_voucher": self.name,
					},
					item=tax,
				)
			)

	def validate_account_details(self):
		for data in self.expenses:
			if not data.cost_center:
				frappe.throw(
					_("Row {0}: {1} is required in the expenses table to book an expense claim.").format(
						data.idx, frappe.bold("Cost Center")
					)
				)

		if self.is_paid:
			if not self.mode_of_payment:
				frappe.throw(_("Mode of payment is required to make a payment").format(self.employee))

	def calculate_total_amount(self):
		self.total_claimed_amount = 0
		self.total_sanctioned_amount = 0
		for d in self.get("expenses"):
			if self.approval_status == "Rejected":
				d.sanctioned_amount = 0.0
			self.total_claimed_amount += flt(d.amount)
			self.total_sanctioned_amount += flt(d.sanctioned_amount)
	@frappe.whitelist()
	def calculate_taxes(self):
		self.total_taxes_and_charges = 0
		self.grand_total = flt(self.total_sanctioned_amount) + flt(self.total_taxes_and_charges) - flt(self.total_advance_amount)
		for tax in self.taxes:
			if tax.rate:
				tax.tax_amount = flt(self.total_sanctioned_amount) * flt(tax.rate / 100)
			if tax.add_or_deduct == "Deduct":
				tax.total = flt(self.total_sanctioned_amount) - flt(tax.tax_amount)
			else:
				tax.total = flt(tax.tax_amount) + flt(self.total_sanctioned_amount)
			self.total_taxes_and_charges += flt(tax.tax_amount)

			if tax.add_or_deduct == "Deduct":
				self.grand_total = (flt(self.total_sanctioned_amount)- flt(self.total_taxes_and_charges)- flt(self.total_advance_amount))
			else:
				self.grand_total = (
					flt(self.total_sanctioned_amount)+ flt(self.total_taxes_and_charges)- flt(self.total_advance_amount)
				)

	def validate_advances(self):
		self.total_advance_amount = 0
		for d in self.get("advances"):
			ref_doc = frappe.db.get_value(
				"Employee Advance",
				d.employee_advance,
				["posting_date", "paid_amount", "claimed_amount", "advance_account"],
				as_dict=1,
			)
			d.posting_date = ref_doc.posting_date
			d.advance_account = ref_doc.advance_account
			d.advance_paid = ref_doc.paid_amount
			d.unclaimed_amount = flt(ref_doc.paid_amount) - flt(ref_doc.claimed_amount)

			if d.allocated_amount and flt(d.allocated_amount) > flt(d.unclaimed_amount):
				frappe.throw(
					_("Row {0}# Allocated amount {1} cannot be greater than unclaimed amount {2}").format(
						d.idx, d.allocated_amount, d.unclaimed_amount
					)
				)

			self.total_advance_amount += flt(d.allocated_amount)
		# frappe.throw(str(self.total_advance_amount)+" "+str(self.total_sanctioned_amount))
		if self.total_advance_amount:
			precision = self.precision("total_advance_amount")
			amount_with_taxes = flt(
				(flt(self.total_sanctioned_amount, precision) + flt(self.total_taxes_and_charges, precision)),
				precision,
			)
			if flt(self.total_advance_amount, precision) > amount_with_taxes:
				frappe.throw(_("Total advance amount cannot be greater than total sanctioned amount"))

	def validate_sanctioned_amount(self):
		for d in self.get("expenses"):
			if flt(d.sanctioned_amount) > flt(d.amount):
				frappe.throw(
					_("Sanctioned Amount cannot be greater than Claim Amount in Row {0}.").format(d.idx)
				)

	def set_expense_account(self, validate=False):
		for expense in self.expenses:
			if not expense.default_account or not validate:
				expense.default_account = get_expense_claim_account(expense.expense_type, self.company)[
					"account"
				]

	def set_travel_reference(self, cancel = 0):
		for item in self.get("expenses"):
			if item.reference_type == "Travel Request" and cancel == 0:
				frappe.db.sql("""
					update `tabTravel Request` 
					set ex_reference = '{}'
					where name = '{}'
				""".format(self.name, item.reference))
			elif item.reference_type == "Travel Request" and cancel == True:
				frappe.db.sql("""
					update `tabTravel Request` 
					set ex_reference = NULL
					where name = '{}'
				""".format(item.reference))

def update_reimbursed_amount(doc, amount):
	doc.total_amount_reimbursed += amount
	frappe.db.set_value(
		"Expense Claim", doc.name, "total_amount_reimbursed", doc.total_amount_reimbursed
	)

	doc.set_status()
	frappe.db.set_value("Expense Claim", doc.name, "status", doc.status)


def get_outstanding_amount_for_claim(claim):
	if isinstance(claim, str):
		claim = frappe.db.get_value(
			"Expense Claim",
			claim,
			(
				"total_sanctioned_amount",
				"total_taxes_and_charges",
				"total_amount_reimbursed",
				"total_advance_amount",
			),
			as_dict=True,
		)

	outstanding_amt = (
		flt(claim.total_sanctioned_amount)
		+ flt(claim.total_taxes_and_charges)
		- flt(claim.total_amount_reimbursed)
		- flt(claim.total_advance_amount)
	)

	return outstanding_amt


@frappe.whitelist()
def make_bank_entry(dt, dn):
	from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

	expense_claim = frappe.get_doc(dt, dn)
	default_bank_cash_account = get_default_bank_cash_account(expense_claim.company, "Bank")
	if not default_bank_cash_account:
		default_bank_cash_account = get_default_bank_cash_account(expense_claim.company, "Cash")

	payable_amount = get_outstanding_amount_for_claim(expense_claim)

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Bank Entry"
	je.company = expense_claim.company
	je.remark = "Payment against Expense Claim: " + dn

	je.append(
		"accounts",
		{
			"account": expense_claim.payable_account,
			"debit_in_account_currency": payable_amount,
			"reference_type": "Expense Claim",
			"party_type": "Employee",
			"party": expense_claim.employee,
			"cost_center": erpnext.get_default_cost_center(expense_claim.company),
			"reference_name": expense_claim.name,
		},
	)

	je.append(
		"accounts",
		{
			"account": default_bank_cash_account.account,
			"credit_in_account_currency": payable_amount,
			"reference_type": "Expense Claim",
			"reference_name": expense_claim.name,
			"balance": default_bank_cash_account.balance,
			"account_currency": default_bank_cash_account.account_currency,
			"cost_center": erpnext.get_default_cost_center(expense_claim.company),
			"account_type": default_bank_cash_account.account_type,
		},
	)

	return je.as_dict()


@frappe.whitelist()
def get_expense_claim_account_and_cost_center(expense_claim_type, company):
	data = get_expense_claim_account(expense_claim_type, company)
	cost_center = erpnext.get_default_cost_center(company)

	return {"account": data.get("account"), "cost_center": cost_center}


@frappe.whitelist()
def get_expense_claim_account(expense_claim_type, company):
	account = frappe.db.get_value(
		"Expense Claim Account", {"parent": expense_claim_type, "company": company}, "default_account"
	)
	if not account:
		frappe.throw(
			_("Set the default account for the {0} {1}").format(
				frappe.bold("Expense Claim Type"), get_link_to_form("Expense Claim Type", expense_claim_type)
			)
		)

	return {"account": account}


@frappe.whitelist()
def get_advances(employee, advance_id=None):
	advance = frappe.qb.DocType("Employee Advance")

	query = frappe.qb.from_(advance).select(
		advance.name,
		advance.posting_date,
		advance.paid_amount,
		advance.pending_amount,
		advance.advance_account,
	)

	if not advance_id:
		query = query.where(
			(advance.docstatus == 1)
			& (advance.employee == employee)
			& (advance.paid_amount > 0)
			& (advance.status.notin(["Claimed", "Returned", "Partly Claimed and Returned"]))
		)
	else:
		query = query.where(advance.name == advance_id)

	return query.run(as_dict=True)


@frappe.whitelist()
def get_expense_claim(
	employee_name, company, employee_advance_name, posting_date, paid_amount, claimed_amount
):
	default_payable_account = frappe.get_cached_value(
		"Company", company, "default_expense_claim_payable_account"
	)
	default_cost_center = frappe.get_cached_value("Company", company, "cost_center")

	expense_claim = frappe.new_doc("Expense Claim")
	expense_claim.company = company
	expense_claim.employee = employee_name
	expense_claim.payable_account = default_payable_account
	expense_claim.cost_center = default_cost_center
	expense_claim.is_paid = 1 if flt(paid_amount) else 0
	expense_claim.append(
		"advances",
		{
			"employee_advance": employee_advance_name,
			"posting_date": posting_date,
			"advance_paid": flt(paid_amount),
			"unclaimed_amount": flt(paid_amount) - flt(claimed_amount),
			"allocated_amount": flt(paid_amount) - flt(claimed_amount),
		},
	)

	return expense_claim


def update_payment_for_expense_claim(doc, method=None):
	"""
	Updates payment/reimbursed amount in Expense Claim
	on Payment Entry/Journal Entry cancellation/submission
	"""
	if doc.doctype == "Payment Entry" and not (doc.payment_type == "Pay" and doc.party):
		return

	payment_table = "accounts" if doc.doctype == "Journal Entry" else "references"
	amount_field = "debit" if doc.doctype == "Journal Entry" else "allocated_amount"
	doctype_field = "reference_type" if doc.doctype == "Journal Entry" else "reference_doctype"

	for d in doc.get(payment_table):
		if d.get(doctype_field) == "Expense Claim" and d.reference_name:
			expense_claim = frappe.get_doc("Expense Claim", d.reference_name)
			if doc.docstatus == 2:
				update_reimbursed_amount(expense_claim, -1 * d.get(amount_field))
			else:
				update_reimbursed_amount(expense_claim, d.get(amount_field))


def validate_expense_claim_in_jv(doc, method=None):
	"""Validates Expense Claim amount in Journal Entry"""
	for d in doc.accounts:
		if d.reference_type == "Expense Claim":
			outstanding_amt = get_outstanding_amount_for_claim(d.reference_name)
			if d.debit > outstanding_amt:
				frappe.throw(
					_(
						"Row No {0}: Amount cannot be greater than the Outstanding Amount against Expense Claim {1}. Outstanding Amount is {2}"
					).format(d.idx, d.reference_name, outstanding_amt)
				)


@frappe.whitelist()
def make_expense_claim_for_delivery_trip(source_name, target_doc=None):
	doc = get_mapped_doc(
		"Delivery Trip",
		source_name,
		{"Delivery Trip": {"doctype": "Expense Claim", "field_map": {"name": "delivery_trip"}}},
		target_doc,
	)

	return doc
