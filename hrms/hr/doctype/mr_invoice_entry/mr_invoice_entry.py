# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import (
	flt,
	money_in_words,
	get_last_day,
	getdate
)
from datetime import datetime
from hrms.hr.hr_custom_functions import get_month_details, get_payroll_settings, get_salary_tax


class MRInvoiceEntry(Document):
	def validate(self):
		self.validate_posting_date()
		self.set_status()
		self.validate_advance_amt()
		self.calculate_totals()

	def calculate_totals(self):
		"""Calculate salary tax (15% of grand_total) and net_payable_amount"""
		total_grand_total = 0
		total_salary_tax = 0
		total_net_payable = 0
		
		for item in self.items:
			if item.grand_total:
				# Calculate salary tax (15% of grand_total)
				item.salary_tax = round(get_salary_tax(flt(item.grand_total) - (flt(item.grand_total) * 0.15)),)
				
				# Calculate net payable amount
				item.net_payable_amount = flt(flt(item.grand_total) - flt(item.salary_tax), 2)- flt(item.total_advance)
				
				# Accumulate totals
				total_grand_total += flt(item.grand_total)
				total_salary_tax += flt(item.salary_tax)
				total_net_payable += flt(item.net_payable_amount)
		
		# Update main totals using the correct field names
		self.grand_total = flt(total_grand_total, 2)
		self.salary_tax = flt(total_salary_tax, 2)
		self.net_payable_amount = flt(total_net_payable, 2)

	def validate_posting_date(self):
		months = [
			"Jan", "Feb", "Mar", "Apr", "May", "Jun",
			"Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
		]
		month = str(int(months.index(self.month)) + 1).rjust(2, "0")

		month_start_date = "-".join([str(self.fiscal_year), month, "01"])
		month_end_date = get_last_day(month_start_date)
	
		if not (getdate(month_start_date) <= getdate(self.posting_date) <= getdate(month_end_date)):
			frappe.throw('Posting date must be between <strong>{}</strong> and <strong>{}</strong>.'.format(
				month_start_date, month_end_date), title="Reset Posting Date")

	def validate_advance_amt(self):
		for a in self.advances:
			if flt(a.allocated_amount) > flt(a.advance_amount):
				frappe.throw("Allocated amount {} cannot be more the Advance amount {} in Row # {}".format(
					frappe.bold(a.allocated_amount),
					frappe.bold(a.advance_amount),
					frappe.bold(a.idx),
				))

	def set_status(self):
		self.status = "Draft"

	def on_submit(self):
		self.db_set("status", "Submitted")
		self.submit_mr_invoice()

	def on_cancel(self):
		frappe.db.sql(
			"""
			UPDATE  
				`tabJournal Entry` 
			SET 
				docstatus = 2 
			WHERE 
				referece_doctype = '{0}'
			""".format(
				self.name
			)
		)

		frappe.db.sql(
			"""
			UPDATE  
				`tabMR Employee Invoice` 
			SET 
				docstatus = 2 
			WHERE 
				mr_invoice_entry = '{0}'
			""".format(
				self.name
			)
		)
		self.db_set("status", "Cancelled")

	@frappe.whitelist()
	def post_to_account(self):
		total_payable_amount = 0
		total_tax_amount = 0
		total_advance_amount = 0
		accounts = []

		# Bank account
		bank_account = frappe.db.get_value("Company", self.company, "default_bank_account")
		if not bank_account:
			frappe.throw('Set default bank account in company {}'.format(self.company))

		# Salary tax account
		salary_tax_account = frappe.db.get_value("Company", self.company, "salary_tax_account")
		if not salary_tax_account:
			frappe.throw('Set salary tax account in company {}'.format(self.company))

		# Payable account
		account_field = "national_wage_payable" if self.muster_roll_group == "National" else "foreign_wage_payable"
		payable_account = frappe.db.get_single_value("Projects Settings", account_field)
		if not payable_account:
			frappe.throw(_("Mr Payable account is not set in Projects Settings"))

		# Loop over MR Employee Invoices
		for d in frappe.db.sql('''
				select name from `tabMR Employee Invoice`
				where docstatus = 1 and mr_invoice_entry = %s
				and branch = %s and outstanding_amount > 0
			''', (self.name, self.branch), as_dict=True):

			mr_invoice = frappe.get_doc("MR Employee Invoice", d.name)
			total_payable_amount += flt(mr_invoice.net_payable_amount, 2)
			total_advance_amount += flt(mr_invoice.total_advance, 2)

			# Debit for employee
			accounts.append({
				"account": payable_account,
				"debit_in_account_currency": flt(mr_invoice.grand_total, 2),
				"cost_center": mr_invoice.cost_center,
				"party_check": 1,
				"party_type": "Muster Roll Employee",
				"party": mr_invoice.mr_employee,
				"party_name": mr_invoice.mr_employee_name,
				"reference_type": mr_invoice.doctype,
				"reference_doctype": mr_invoice.name,
			})

			# Credit for salary tax if exists
			if mr_invoice.salary_tax and mr_invoice.salary_tax > 0:
				total_tax_amount += flt(mr_invoice.salary_tax, 2)
				accounts.append({
					"account": salary_tax_account,
					"credit_in_account_currency": flt(mr_invoice.salary_tax, 2),
					"cost_center": mr_invoice.cost_center,
					"party_check": 1,
					"party_type": "Muster Roll Employee",
					"party": mr_invoice.mr_employee,
					"party_name": mr_invoice.mr_employee_name,
					"reference_type": mr_invoice.doctype,
					"reference_doctype": mr_invoice.name,
				})

		# Add single bank credit line with sum of all amounts
		total_bank_amount = flt(total_payable_amount  + total_advance_amount, 2)
		accounts.append({
			"account": bank_account,
			"credit_in_account_currency": total_bank_amount,
			"cost_center": self.cost_center
		})

		# Create Journal Entry
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"naming_series": "Bank Payment Voucher",
			"title": "MR Employee Invoice Payment",
			"user_remark": "MR Employee Invoice Payment of {} for year {} (Tax: {}, Advance: {})".format(
				self.month, self.fiscal_year, total_tax_amount, total_advance_amount
			),
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(total_bank_amount),
			"branch": self.branch,
			"reference_type": self.doctype,
			"reference_doctype": self.name,
			"accounts": accounts
		})
		je.insert()

		# Update invoice statuses
		for d in frappe.db.sql('''
				select name from `tabMR Employee Invoice`
				where docstatus = 1 and mr_invoice_entry = %s
				and branch = %s and outstanding_amount > 0
			''', (self.name, self.branch), as_dict=True):
			frappe.db.set_value("MR Employee Invoice", d.name, {
				"payment_status": "Paid",
				"outstanding_amount": 0
			})

		self.db_set("status", "Paid")
		frappe.msgprint(_('Journal Entry {0} posted to accounts').format(
			frappe.get_desk_link("Journal Entry", je.name)))
			
	# @frappe.whitelist()
	# def post_to_account(self):
	# 	total_payable_amount = 0
	# 	accounts = []
		
	# 	# Use the bank account from the document or fallback to company default
	# 	bank_account = frappe.db.get_value("Company", self.company, "default_bank_account")
	# 	if not bank_account:
	# 		frappe.throw('Set default bank account in company {}'.format(self.company))
		
	# 	# Get the payable account based on muster roll group
	# 	account_field = "national_wage_payable" if self.muster_roll_group == "National" else "foreign_wage_payable"
	# 	payable_account = frappe.db.get_single_value("Projects Settings", account_field)
		
	# 	if not payable_account:
	# 		frappe.throw(_("Mr Payable account is not set in Projects Settings"))
		
	# 	# Get MR Employee Invoices for this entry
	# 	for d in frappe.db.sql('''
	# 			select name from `tabMR Employee Invoice` 
	# 			where docstatus = 1 and mr_invoice_entry = '{}'
	# 			and branch = '{}' and outstanding_amount > 0 
	# 			'''.format(self.name, self.branch), as_dict=True):
	# 		mr_invoice = frappe.get_doc("MR Employee Invoice", d.name)
	# 		total_payable_amount += flt(mr_invoice.grand_total, 2)
			
	# 		# Add payable entries for each employee
	# 		accounts.append({
	# 			"account": payable_account,  # Using dynamic account based on muster roll group
	# 			"debit_in_account_currency": flt(mr_invoice.grand_total, 2),
	# 			"cost_center": mr_invoice.cost_center,
	# 			"party_check": 1,
	# 			"party_type": "Muster Roll Employee",
	# 			"party": mr_invoice.mr_employee,
	# 			"party_name": mr_invoice.mr_employee_name,
	# 			"reference_type": mr_invoice.doctype,
	# 			"reference_doctype": mr_invoice.name,
	# 		})
		
	# 	# Add bank account entry
	# 	accounts.append({
	# 		"account": bank_account,
	# 		"credit_in_account_currency": flt(total_payable_amount, 2),
	# 		"cost_center": self.cost_center
	# 	})
		
	# 	# Create Journal Entry
	# 	je = frappe.new_doc("Journal Entry")
	# 	je.flags.ignore_permissions = 1
	# 	je.update({
	# 		"doctype": "Journal Entry",
	# 		"voucher_type": "Bank Entry",
	# 		"naming_series": "Bank Payment Voucher",
	# 		"title": "MR Employee Invoice Payment ",
	# 		"user_remark": "Note: MR Employee Invoice Payment of {} for year {}".format(self.month, self.fiscal_year),
	# 		"posting_date": self.posting_date,
	# 		"company": self.company,
	# 		"total_amount_in_words": money_in_words(total_payable_amount),
	# 		"branch": self.branch,
	# 		"reference_type": self.doctype,
	# 		"reference_doctype": self.name,
	# 		"accounts": accounts
	# 	})
	# 	je.insert()
		
	# 	# Update MR Employee Invoice statuses
	# 	for d in frappe.db.sql('''
	# 			select name from `tabMR Employee Invoice` 
	# 			where docstatus = 1 and mr_invoice_entry = '{}'
	# 			and branch = '{}' and outstanding_amount > 0 
	# 			'''.format(self.name, self.branch), as_dict=True):
	# 		frappe.db.set_value("MR Employee Invoice", d.name, {
	# 			"payment_status": "Paid",
	# 			"outstanding_amount": 0
	# 		})
		
	# 	self.db_set("status", "Paid")
	# 	frappe.msgprint(_('Journal Entry {0} posted to accounts').format(
	# 		frappe.get_desk_link("Journal Entry", je.name)))

	# @frappe.whitelist()
	# def post_to_account(self):
	# 	total_payable_amount = 0
	# 	total_tax_amount = 0
	# 	accounts = []
		
	# 	# Use the bank account from the document or fallback to company default
	# 	bank_account = frappe.db.get_value("Company", self.company, "default_bank_account")
	# 	if not bank_account:
	# 		frappe.throw('Set default bank account in company {}'.format(self.company))
		
	# 	# Get salary tax account from company
	# 	salary_tax_account = frappe.db.get_value("Company", self.company, "salary_tax_account")
	# 	if not salary_tax_account:
	# 		frappe.throw('Set salary tax account in company {}'.format(self.company))
		
	# 	# Get the payable account based on muster roll group
	# 	account_field = "national_wage_payable" if self.muster_roll_group == "National" else "foreign_wage_payable"
	# 	payable_account = frappe.db.get_single_value("Projects Settings", account_field)
		
	# 	if not payable_account:
	# 		frappe.throw(_("Mr Payable account is not set in Projects Settings"))
		
	# 	# Get MR Employee Invoices for this entry
	# 	for d in frappe.db.sql('''
	# 			select name from `tabMR Employee Invoice` 
	# 			where docstatus = 1 and mr_invoice_entry = '{}'
	# 			and branch = '{}' and outstanding_amount > 0 
	# 			'''.format(self.name, self.branch), as_dict=True):
	# 		mr_invoice = frappe.get_doc("MR Employee Invoice", d.name)
	# 		total_payable_amount += flt(mr_invoice.grand_total, 2)
			
	# 		# Add payable entries for each employee
	# 		accounts.append({
	# 			"account": payable_account,  # Using dynamic account based on muster roll group
	# 			"debit_in_account_currency": flt(mr_invoice.grand_total, 2),
	# 			"cost_center": mr_invoice.cost_center,
	# 			"party_check": 1,
	# 			"party_type": "Muster Roll Employee",
	# 			"party": mr_invoice.mr_employee,
	# 			"party_name": mr_invoice.mr_employee_name,
	# 			"reference_type": mr_invoice.doctype,
	# 			"reference_doctype": mr_invoice.name,
	# 		})
			
	# 		# If salary tax exists for this invoice, add tax entry
	# 		if mr_invoice.salary_tax and mr_invoice.salary_tax > 0:
	# 			total_tax_amount += flt(mr_invoice.salary_tax, 2)
	# 			accounts.append({
	# 				"account": salary_tax_account,
	# 				"credit_in_account_currency": flt(mr_invoice.salary_tax, 2),
	# 				"cost_center": mr_invoice.cost_center,
	# 				"party_check": 1,
	# 				"party_type": "Muster Roll Employee",
	# 				"party": mr_invoice.mr_employee,
	# 				"party_name": mr_invoice.mr_employee_name,
	# 				"reference_type": mr_invoice.doctype,
	# 				"reference_doctype": mr_invoice.name,
	# 			})
		
	# 	# Add bank account entry (total payable + total tax)
	# 	total_bank_amount = flt(total_payable_amount + total_tax_amount, 2)
	# 	accounts.append({
	# 		"account": bank_account,
	# 		"credit_in_account_currency": flt(mr_invoice.net_payable_amount, 2),
	# 		"cost_center": self.cost_center
	# 	})
	# 	accounts.append({
	# 		"account": bank_account,
	# 		"credit_in_account_currency": flt(mr_invoice.total_advance, 2),
	# 		"cost_center": self.cost_center
	# 	})
		
	# 	# Create Journal Entry
	# 	je = frappe.new_doc("Journal Entry")
	# 	je.flags.ignore_permissions = 1
	# 	je.update({
	# 		"doctype": "Journal Entry",
	# 		"voucher_type": "Bank Entry",
	# 		"naming_series": "Bank Payment Voucher",
	# 		"title": "MR Employee Invoice Payment ",
	# 		"user_remark": "Note: MR Employee Invoice Payment of {} for year {} (Including Tax: {})".format(
	# 			self.month, self.fiscal_year, total_tax_amount
	# 		),
	# 		"posting_date": self.posting_date,
	# 		"company": self.company,
	# 		"total_amount_in_words": money_in_words(total_bank_amount),
	# 		"branch": self.branch,
	# 		"reference_type": self.doctype,
	# 		"reference_doctype": self.name,
	# 		"accounts": accounts
	# 	})
	# 	je.insert()
		
	# 	# Update MR Employee Invoice statuses
	# 	for d in frappe.db.sql('''
	# 			select name from `tabMR Employee Invoice` 
	# 			where docstatus = 1 and mr_invoice_entry = '{}'
	# 			and branch = '{}' and outstanding_amount > 0 
	# 			'''.format(self.name, self.branch), as_dict=True):
	# 		frappe.db.set_value("MR Employee Invoice", d.name, {
	# 			"payment_status": "Paid",
	# 			"outstanding_amount": 0
	# 		})
		
	# 	self.db_set("status", "Paid")
	# 	frappe.msgprint(_('Journal Entry {0} posted to accounts').format(
	# 		frappe.get_desk_link("Journal Entry", je.name)))

	def submit_mr_invoice(self):
		bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		if not bank_account:
			bank_account = frappe.db.get_value("Company", self.company, "default_bank_account")
		
		successful = failed = 0
		for inv in self.items:
			error = None
			try:
				mr_invoice = frappe.get_doc(
					"MR Employee Invoice",
					{
						"mr_employee": inv.mr_employee,
						"docstatus": 0,
						"branch": self.branch,
						"mr_invoice_entry": self.name,
					},
				)
				mr_invoice.submit()
				successful += 1
			except Exception as e:
				error = e
				failed += 1
			inv_item = frappe.get_doc(inv.doctype, inv.name)
			if error:
				inv.error_message = str(error)
				inv_item.db_set("submission_status", "Failed")
			else:
				inv_item.db_set("submission_status", "Successful")
		
		if successful > 0:
			self.db_set("mr_invoice_submit", 1)

	@frappe.whitelist()
	def get_mr_employee(self):
		cond = ""
		if not self.branch or not self.month or not self.fiscal_year:
			frappe.throw("Either Branch/Month/Fiscal Year is missing")
		
		if self.individual == 1:
			cond = "and name = '{}'".format(self.mr_employee)
		
		self.set("items", [])
		mr_cond = ""
		
		if self.muster_roll_group:
			mr_cond += " and muster_roll_group = '{}'".format(self.muster_roll_group)
		if self.team_lead:
			mr_cond += " and team_lead = '{}'".format(self.team_lead)
		
		# Get MR employees without existing invoices for this month/year
		for e in frappe.db.sql(
			"""
			SELECT 
				mre.name AS mr_employee,
				mre.person_name AS mr_employee_name,
				mre.rate_per_day,
				mre.rate_per_hour
			FROM `tabMuster Roll Employee` mre
			LEFT JOIN `tabMR Employee Invoice` e
				ON e.mr_employee = mre.name
				AND e.month = %s
				AND e.fiscal_year = %s
				AND e.docstatus != 2
			WHERE mre.status = 'Active'
				AND mre.branch = %s
				{0} {1}
				AND e.name IS NULL
			ORDER BY mre.person_name
			""".format(cond, mr_cond),
			(self.month, self.fiscal_year, self.branch),
			as_dict=True,
		):
			self.append("items", e)

	@frappe.whitelist()
	def get_advance(self):
		self.set("advances", [])
		for item in self.items:
			res = self.get_advance_entries(item.mr_employee)
			for d in res:
				advance_row = {
					"doctype": self.doctype + " Advance",
					"reference_type": d.reference_type,
					"reference_name": d.reference_name,
					"party_type": "Muster Roll Employee",
					"party": d.mr_employee,
					"party_name": d.mr_employee_name,
					"cost_center": d.cost_center,
					"advance_amount": flt(d.advance_amount),
					"advance_account": d.account,
				}
				self.append("advances", advance_row)
	
	def get_advance_entries(self, mr_employee):
		national_mr_emp_advance = frappe.db.sql("""
			select
				'Muster Roll Advance' as reference_type, 
				name as reference_name, 
				advance_account as account, 
				balance_amount as advance_amount, 
				cost_center, 
				mr_employee, 
				mr_employee_name
			from 
				`tabMuster Roll Advance` 
			where
				docstatus = 1 
				and balance_amount > 0 
				and mr_employee = %s
		""", mr_employee, as_dict=True)
		
		non_national_mr_emp_advance = frappe.db.sql("""
			select
				'Muster Roll Advance' as reference_type, 
				adv.name as reference_name, 
				adv.advance_account as account, 
				adv_item.balance_amount as advance_amount, 
				adv.cost_center, 
				adv_item.mr_employee, 
				adv_item.mr_employee_name
			from 
				`tabMuster Roll Advance` adv, 
				`tabMuster Roll Advance Item` adv_item  
			where
				adv_item.parent = adv.name 
				and adv.journal_entry_status = "Paid"
				and adv.docstatus = 1 
				and adv_item.balance_amount > 0 
				and adv_item.mr_employee = %s
		""", mr_employee, as_dict=True)
		
		total_advance = national_mr_emp_advance + non_national_mr_emp_advance
		
		return total_advance

	@frappe.whitelist()
	def create_mr_invoice(self):
		self.check_permission("write")

		account = "national_wage_payable" if self.muster_roll_group == "National" else "foreign_wage_payable"
		credit_account = frappe.db.get_single_value("Projects Settings", account)

		if not credit_account:
			frappe.throw(_("Mr Payable account is not set in Projects Settings"))

		# Preload all child data into dicts keyed by employee
		deductions_map = {}
		for d in self.deductions:
			deductions_map.setdefault(d.mr_employee, []).append(d)

		advances_map = {}
		for adv in self.advances:
			advances_map.setdefault(adv.party, []).append(adv)

		arrears_map = {}
		for a in getattr(self, "arrears_and_allowance", []):
			arrears_map.setdefault(a.mr_employee, []).append(a)

		successful = failed = 0
		count = 0

		for item in self.items:
			count += 1
			args_item = frappe._dict({
				"mr_invoice_entry": self.name,
				"doctype": "MR Employee Invoice",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"posting_date": self.posting_date,
				"company": self.company,
				"status": "Draft",
				"fiscal_year": self.fiscal_year,
				"month": self.month,
				"currency": self.currency,
				"credit_account": credit_account,
				"mr_employee": item.mr_employee,
				"mr_employee_name": item.mr_employee_name,
			})

			try:
				mr_invoice = frappe.get_doc(args_item)
				
				# Get attendance and OT
				mr_invoice.get_attendance()
				mr_invoice.get_ot()

				# Add child tables from preloaded dicts
				mr_invoice.set("deductions", [])
				for d in deductions_map.get(item.mr_employee, []):
					mr_invoice.append("deductions", {
						"account": d.account,
						"amount": d.amount,
						"remarks": d.remarks,
					})

				mr_invoice.set("advances", [])
				for adv in advances_map.get(item.mr_employee, []):
					mr_invoice.append("advances", {
						"reference_type": adv.reference_type,
						"reference_name": adv.reference_name,
						"account": adv.advance_account,
						"amount": adv.allocated_amount,
						"remarks": adv.remarks,
					})

				mr_invoice.set("arrears_and_allowance", [])
				for a in arrears_map.get(item.mr_employee, []):
					mr_invoice.append("arrears_and_allowance", {
						"account": a.account,
						"amount": a.amount,
						"remarks": a.remarks,
					})

				mr_invoice.save(ignore_permissions=True)
				
				# Calculate salary tax for this invoice
				salary_tax = round(get_salary_tax(flt(mr_invoice.grand_total) - (flt(mr_invoice.grand_total) * 0.15)),)
				net_payable = flt(flt(mr_invoice.grand_total) - salary_tax -  flt(mr_invoice.total_advance), 2)

				# Update totals for the item - using correct field names
				item.db_set({
					"total_days_worked": mr_invoice.total_days_worked,
					"total_daily_wage_amount": mr_invoice.total_daily_wage_amount,
					"other_deduction": mr_invoice.other_deduction,
					"tds_amount": mr_invoice.total_tds_amount,
					"total_advance": mr_invoice.total_advance,
					"grand_total": mr_invoice.grand_total,
					"salary_tax": salary_tax,
					"net_payable_amount": net_payable,
					"total_ot_hrs": mr_invoice.total_ot_hrs,
					"total_ot_amount": mr_invoice.total_ot_amount,
					"reference": mr_invoice.name,
					"creation_status": "Successful",
					"error_message": "",
				})

				successful += 1

				if count % 50 == 0:
					frappe.db.commit()

			except Exception:
				error = frappe.get_traceback()
				failed += 1
				frappe.log_error(error, f"Error creating MR Invoice for {item.mr_employee}")

				# Mark item as failed immediately
				item.db_set({
					"creation_status": "Failed",
					"error_message": error
				})

		# Recalculate main totals using the correct field names
		self.calculate_totals()
		self.save()
		
		if successful > 0:
			self.mr_invoice_created = 1
		
		frappe.db.commit()
		self.reload()