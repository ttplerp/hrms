# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, flt, get_link_to_form, today, cint

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
		self.set("__onload", frappe._dict())
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
		self.calculate_gst_amount()
		self.set_cost_center()
		self.calculate_taxes()
		self.set_status()
		self.update_ref_doc()
		if self.task and not self.project:
			self.project = frappe.db.get_value("Task", self.task, "project")

	def validate_references(self):
		for a in self.expenses:
			if a.expense_type in ('Leave Encashment','Travel','Meeting & Seminars','Training') and not a.reference:
				frappe.throw(
					_("Cannot create Expense Claim for {} directly from Expense Claim.".format(a.expense_type)),
					title="Invalid Operation"
				)

	def set_status(self, update=False):
		status = {"0": "Draft", "1": "Submitted", "2": "Cancelled"}[cstr(self.docstatus or 0)]

		precision = self.precision("grand_total")

		if (
			self.is_paid
			or (
				flt(self.total_sanctioned_amount > 0)
				and (
					(
						self.docstatus == 1
						and flt(self.grand_total, precision) == flt(self.total_amount_reimbursed, precision)
					)
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

	def set_payable_account(self):
		if not self.payable_account and not self.is_paid:
			self.payable_account = frappe.get_cached_value(
				"Company", self.company, "default_expense_claim_payable_account"
			)

	def set_cost_center(self):
		if not self.cost_center:
			self.cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

	def on_submit(self):
		self.check_for_total_sanctioned_amount()
		self.update_task_and_project()
		self.make_gl_entries()
		self.post_accounts_entry()
		if self.is_paid:
			update_reimbursed_amount(self, self.grand_total)

		self.set_status(update=True)
		self.update_claimed_amount_in_employee_advance()
		self.set_travel_reference()
		self.update_ref_doc()

	def check_for_total_sanctioned_amount(self):
		if flt(self.total_sanctioned_amount) == 0:
			frappe.throw(_("The <b>Total Sanctioned Amount</b> cannot be less than or equal to 0"))

	def before_cancel(self):
		for a in self.expenses:
			if a.reference_type == 'Leave Encashment':
				frappe.db.sql("""
					UPDATE `tabLeave Encashment` 
					SET expense_claim = NULL 
					WHERE name = %s
				""", a.reference)
		
		if frappe.db.exists("Journal Entry Account", {
			"reference_type": "Expense Claim",
			"reference_name": self.name
		}):
			ref_je = frappe.db.get_value(
				"Journal Entry Account",
				{"reference_type": "Expense Claim", "reference_name": self.name},
				"parent"
			)
			doc = frappe.get_doc("Journal Entry", ref_je)
			if doc.docstatus != 2:
				frappe.throw(_("{} Exists against this document").format(
					frappe.get_desk_link("Journal Entry", ref_je)
				))

	def on_cancel(self):
		self.update_task_and_project()
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")
		if self.payable_account:
			self.make_gl_entries(cancel=True)

		if self.is_paid:
			update_reimbursed_amount(self, -1 * self.grand_total)

		self.update_claimed_amount_in_employee_advance(cancel=True)
		self.set_travel_reference(cancel=True)

	def update_ref_doc(self):
		for d in self.expenses:
			self.ref_doc = d.expense_type
			break

	def post_accounts_entry(self):
		"""Create Journal Entry for expense claim payment"""
		if not self.cost_center:
			frappe.throw(_("Setup Cost Center for employee in Employee Information"))

		expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		if not expense_bank_account:
			expense_bank_account = frappe.db.get_value(
				"Company", {'name': self.company}, "default_bank_account"
			)
			if not expense_bank_account:
				frappe.throw(_("Setup Expense Bank Account in Branch or Default Expense Bank Account in Company Accounts Settings"))

		employee_payable_account = frappe.db.get_value("Company", self.company, "default_bank_account")
		account_imprest = frappe.db.get_value("Company", self.company, "imprest_advance_account")
		
		# Get expense type
		ec_type = ''
		mis_account = ''
		for data in self.expenses:
			ec_type = data.expense_type
			mis_account = data.default_account

		# Create Journal Entry
		if flt(self.total_claimed_amount) > 0:
			jeb = frappe.new_doc("Journal Entry")
			jeb.flags.ignore_permissions = 1
			jeb.title = f"Expense Claim Payment({self.employee_name} - {self.name})"
			jeb.voucher_type = "Bank Entry"
			jeb.naming_series = "Bank Payment Voucher"
			
			expense_claim_type = ""
			for b in self.expenses:
				if b.is_stock_item:
					expense_claim_type = b.item_code
				else:
					expense_claim_type = b.expense_type
					
			jeb.remark = f'Payment against Expense Claim({expense_claim_type}) : {self.name}'
			jeb.user_remark = f'Payment against Expense Claim({expense_claim_type}) : {self.name}'
			jeb.posting_date = today()
			jeb.branch = self.branch
			jeb_cost_center = frappe.db.get_value("Branch", jeb.branch, "cost_center")

			# Handle Imprest claims
			if ec_type == 'Imprest':
				jeb.append("accounts", {
					"account": mis_account,
					"cost_center": self.cost_center,
					"reference_type": "Expense Claim",
					"reference_name": self.name,
					"debit_in_account_currency": self.total_claimed_amount,
					"debit": self.total_claimed_amount,
					"user_remark": f'Payment against Expense Claim({expense_claim_type}) : {self.name}',
					"business_activity": "Common",
				})
				
				jeb.append("accounts", {
					"account": account_imprest,
					"cost_center": self.cost_center,
					"credit_in_account_currency": self.total_advance_amount if self.total_advance_amount > 0 else self.total_claimed_amount,
					"credit": self.total_advance_amount if self.total_advance_amount > 0 else self.total_claimed_amount,
					"business_activity": "Common",
					"party_type": "Employee",
					"user_remark": f'Payment against Expense Claim({expense_claim_type}) : {self.name}',
					"party": self.employee,
					"party_name": self.employee_name
				})
				
				if self.total_advance_amount > 0 and flt(self.total_advance_amount) != self.total_claimed_amount:
					jeb.append("accounts", {
						"account": employee_payable_account,
						"cost_center": self.cost_center,
						"credit_in_account_currency": self.grand_total,
						"credit": self.grand_total,
						"user_remark": f'Payment against Expense Claim({expense_claim_type}) : {self.name}',
						"business_activity": "Common",
						"party_type": "Employee",
						"party": self.employee,
						"party_name": self.employee_name
					})
			else:
				# Handle regular expense claims
				amount = 0
				advance_amount = 0
				advance = 0
				advance_doc = ""
				
				if len(self.advances) > 0:
					advance = 1
					for a in self.advances:
						advance_doc = frappe.get_doc("Employee Advance", a.employee_advance)
				
				if self.grand_total == 0 and advance == 1:
					amount = self.total_sanctioned_amount
					advance_amount = self.total_advance_amount
					employee_payable_account = advance_doc.advance_account
				else:
					amount = self.grand_total
					advance_amount = self.grand_total
				
				if self.grand_total == 0 and advance == 1:
					for b in self.expenses:
						jeb.append("accounts", {
							"account": frappe.db.get_value(
								"Expense Claim Account", 
								{"parent": b.expense_type}, 
								"default_account"
							),
							"reference_type": "Expense Claim",
							"reference_name": self.name,
							"cost_center": self.cost_center,
							"debit_in_account_currency": flt(b.amount, 2),
							"debit": flt(b.amount, 2),
							"business_activity": "Common",
							"party_type": "Employee",
							"user_remark": f'Payment against Expense Claim({expense_claim_type}) : {self.name}',
							"party": self.employee,
							"party_name": self.employee_name
						})
				else:
					jeb.append("accounts", {
						"account": self.payable_account,
						"reference_type": "Expense Claim",
						"reference_name": self.name,
						"cost_center": self.cost_center,
						"debit_in_account_currency": amount,
						"debit": amount,
						"business_activity": "Common",
						"party_type": "Employee",
						"user_remark": f'Payment against Expense Claim({expense_claim_type}) : {self.name}',
						"party": self.employee,
						"party_name": self.employee_name
					})
					
				jeb.append("accounts", {
					"account": employee_payable_account,
					"cost_center": self.cost_center,
					"credit_in_account_currency": advance_amount,
					"credit": advance_amount,
					"user_remark": f'Payment against Expense Claim({expense_claim_type}) : {self.name}',
					"business_activity": "Common",
				})
				
			jeb.insert()
			self.db_set("payment_journal", jeb.name)
			frappe.db.commit()

	def update_claimed_amount_in_employee_advance(self, cancel=False):
		for d in self.get("advances"):
			frappe.get_doc("Employee Advance", d.employee_advance).update_claimed_amount(cancel=cancel)

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
		ec_type = ''
		for d in self.expenses:
			ec_type = d.expense_type
			break
			
		if ec_type != 'Imprest' and flt(self.total_sanctioned_amount) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		"""Generate GL entries with proper tax handling"""
		gl_entry = []
		self.validate_account_details()

		total_debits = 0
		total_credits = 0

		# 1. Expense entries (Debits)
		for data in self.expenses:
			debit_account = data.default_account
			
			# Handle Travel Request special accounts
			if data.reference_type == "Travel Request":
				travel_type = frappe.db.get_value(
					"Travel Request", 
					{'name': data.reference}, 
					"travel_type"
				)
				if travel_type == "Domestic":
					debit_account = frappe.db.get_value(
						"Company", 
						{'name': self.company}, 
						"travel_in_country_account"
					)
				elif travel_type == "International":
					debit_account = frappe.db.get_value(
						"Company", 
						{'name': self.company}, 
						"travel_out_country_account"
					)

			gl_entry.append(
				self.get_gl_dict(
					{
						"account": debit_account if debit_account else data.default_account,
						"debit": data.sanctioned_amount,
						"debit_in_account_currency": data.sanctioned_amount,
						"against": self.employee,
						"cost_center": data.cost_center or self.cost_center,
					},
					item=data,
				)
			)
			total_debits += data.sanctioned_amount

		# 2. Tax entries
		for tax in self.taxes:
			if tax.add_or_deduct == "Add":
				# Add taxes (like GST) are debited (expense)
				gl_entry.append(
					self.get_gl_dict(
						{
							"account": tax.account_head,
							"debit": tax.tax_amount,
							"debit_in_account_currency": tax.tax_amount,
							"against": self.employee,
							"cost_center": self.cost_center,
							"against_voucher_type": self.doctype,
							"against_voucher": self.name,
						},
						item=tax,
					)
				)
				total_debits += tax.tax_amount
			else:
				# Deduct taxes (like TDS) are credited (liability)
				gl_entry.append(
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
				total_credits += tax.tax_amount

		# 3. Advance entries (Credits)
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
			total_credits += data.allocated_amount

		# 4. Payable entry (Credit - balance)
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
			total_credits += self.grand_total

		# Verify accounting equation
		if abs(total_debits - total_credits) > 0.01:
			frappe.log_error(
				title="GL Entry Mismatch",
				message=f"Expense Claim {self.name}: Debits={total_debits}, Credits={total_credits}, Difference={total_debits - total_credits}"
			)

		return gl_entry
		
	def calculate_gst_amount(self):
		"""Calculate GST amount for each expense row (5% of amount) only if GST account exists in taxes"""
		# Check if there's any tax with GST in account head
		has_gst_tax = False
		
		# Check if taxes table exists and has entries
		if self.get("taxes"):
			for tax in self.taxes:
				# Check if account head contains 'GST' (case insensitive)
				if tax.account_head and "GST" in tax.account_head.upper():
					has_gst_tax = True
					break
		
		# Only calculate GST if GST account exists in taxes
		for expense in self.get("expenses"):
			if has_gst_tax and expense.amount:
				expense.gst_amount = flt(expense.amount) * 0.05
			else:
				expense.gst_amount = 0

	def validate_account_details(self):
		for data in self.expenses:
			if not data.cost_center:
				frappe.throw(
					_("Row {0}: {1} is required in the expenses table to book an expense claim.").format(
						data.idx, frappe.bold("Cost Center")
					)
				)

		if self.is_paid and not self.mode_of_payment:
			frappe.throw(_("Mode of payment is required to make a payment"))

	def calculate_total_amount(self):
		"""Calculate total claimed and sanctioned amounts"""
		self.total_claimed_amount = 0
		self.total_sanctioned_amount = 0
		
		for d in self.get("expenses"):
			if self.approval_status == "Rejected":
				d.sanctioned_amount = 0.0
				
			self.total_claimed_amount += flt(d.amount)
			self.total_sanctioned_amount += flt(d.sanctioned_amount)
		
		# Update database
		self.db_set("total_claimed_amount", self.total_claimed_amount, update_modified=False)
		self.db_set("total_sanctioned_amount", self.total_sanctioned_amount, update_modified=False)

	@frappe.whitelist()
	def calculate_taxes(self):
		"""
		Calculate taxes and grand total for expense claim
		Fixed version with proper tax handling
		"""
		self.total_taxes_and_charges = 0
		
		# Ensure sanctioned amount is calculated
		if not self.total_sanctioned_amount:
			self.calculate_total_amount()
		
		# Calculate tax amounts
		for tax in self.taxes:
			if tax.rate:
				tax.tax_amount = flt(self.total_sanctioned_amount) * flt(tax.rate / 100)
			
			# Calculate running total for display
			if tax.add_or_deduct == "Deduct":
				tax.total = flt(self.total_sanctioned_amount) - flt(tax.tax_amount)
			else:  # Add
				tax.total = flt(tax.tax_amount) + flt(self.total_sanctioned_amount)
		
		# Calculate additions and deductions separately
		total_additions = 0
		total_deductions = 0
		
		for tax in self.taxes:
			tax_amount = flt(tax.tax_amount)

			if tax.add_or_deduct == "Add":
				total_additions += tax_amount
				self.total_taxes_and_charges += tax_amount
			else:  # Deduct
				total_deductions += tax_amount
				self.total_taxes_and_charges -= tax_amount

		
		# Grand Total = Sanctioned Amount + Additions - Deductions - Advances
		self.grand_total = (
			flt(self.total_sanctioned_amount) + 
			total_additions - 
			total_deductions - 
			flt(self.total_advance_amount)
		)
		
		# Update database
		self.db_set("total_taxes_and_charges", self.total_taxes_and_charges, update_modified=False)
		self.db_set("grand_total", self.grand_total, update_modified=False)

	def validate_advances(self):
		"""Validate advance allocations"""
		self.total_advance_amount = 0
		
		for d in self.get("advances"):
			ref_doc = frappe.db.get_value(
				"Employee Advance",
				d.employee_advance,
				["posting_date", "paid_amount", "claimed_amount", "advance_account"],
				as_dict=1,
			)
			
			if ref_doc:
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
		
		# Validate advance amount against total payable
		if self.total_advance_amount:
			total_additions = sum(flt(t.tax_amount) for t in self.taxes if t.add_or_deduct == "Add")
			total_deductions = sum(flt(t.tax_amount) for t in self.taxes if t.add_or_deduct == "Deduct")
			
			total_payable = flt(self.total_sanctioned_amount) + total_additions - total_deductions
			
			if flt(self.total_advance_amount) > total_payable:
				frappe.throw(
					_("Total advance amount ({0}) cannot be greater than total payable amount ({1})").format(
						self.total_advance_amount, total_payable
					)
				)
		
		self.db_set("total_advance_amount", self.total_advance_amount, update_modified=False)

	def validate_sanctioned_amount(self):
		for d in self.get("expenses"):
			if flt(d.sanctioned_amount) > flt(d.amount):
				frappe.throw(
					_("Sanctioned Amount cannot be greater than Claim Amount in Row {0}.").format(d.idx)
				)

	def set_expense_account(self, validate=False):
		for expense in self.expenses:
			if not expense.default_account or not validate:
				expense.default_account = get_expense_claim_account(expense.expense_type, self.company)["account"]

	def set_travel_reference(self, cancel=False):
		for item in self.get("expenses"):
			if item.reference_type == "Travel Request":
				if not cancel:
					frappe.db.sql("""
						UPDATE `tabTravel Request` 
						SET ex_reference = %s
						WHERE name = %s
					""", (self.name, item.reference))
				else:
					frappe.db.sql("""
						UPDATE `tabTravel Request` 
						SET ex_reference = NULL
						WHERE name = %s
					""", item.reference)


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
	je.branch = expense_claim.branch
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
		"Expense Claim Account", 
		{"parent": expense_claim_type, "company": company}, 
		"default_account"
	)
	
	if not account:
		frappe.throw(
			_("Set the default account for the {0} {1}").format(
				frappe.bold("Expense Claim Type"), 
				get_link_to_form("Expense Claim Type", expense_claim_type)
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
		advance.claimed_amount
	)

	if not advance_id:
		query = query.where(
			(advance.docstatus == 1)
			& (advance.employee == employee)
			& (advance.paid_amount > 0)
			& (advance.expenses_claimed == 0)
			& (advance.advance_type == 'Imprest Advance')
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
			ex_claim = frappe.get_doc('Expense Claim', d.reference_name)
			
			# Skip validation for Imprest claims
			is_imprest = False
			for row in ex_claim.get('expenses'):
				if row.expense_type == 'Imprest':
					is_imprest = True
					break
					
			if not is_imprest:
				outstanding_amt = get_outstanding_amount_for_claim(d.reference_name)
				if d.debit > outstanding_amt and ex_claim.grand_total > 0:
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


def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user
		
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return None
		
	if "HR User" in user_roles or "HR Manager" in user_roles or "Accounts User" in user_roles:
		return None

	return """(
		`tabExpense Claim`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabExpense Claim`.employee
				and `tabEmployee`.user_id = '{user}')
	)""".format(user=user)