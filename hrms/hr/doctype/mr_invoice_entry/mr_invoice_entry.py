# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import (
	add_days,
	add_months,
	add_years,
	cint,
	cstr,
	date_diff,
	flt,
	formatdate,
	get_last_day,
	get_timestamp,
	getdate,
	nowdate,
	money_in_words
)
class MRInvoiceEntry(Document):
	pass
	def validate(self):
		self.set_mr_payable_account()
	
	def set_mr_payable_account(self):
		credit_account = frappe.db.get_value("Company", self.company, "mr_salary_payable_account")
		if credit_account:
			self.db_set("credit_account", credit_account)
		else:
			frappe.throw("Please set Muster Roll Payable Account in Company Settings")

	def on_submit(self):
		self.submit_mr_invoice()

	def submit_mr_invoice(self):
		bank_account = frappe.db.get_value("Branch",self.branch,"expense_bank_account")
		if not bank_account:
			bank_account = frappe.db.get_value("Company",self.company,"default_bank_account")
		successful = failed = 0
		for inv in self.items:
			error = None
			try:
				mr_invoice = frappe.get_doc("MR Employee Invoice",{"mr_employee":inv.mr_employee,"docstatus":0,"branch":self.branch, "mr_invoice_entry":self.name})
				mr_invoice.submit()
				successful += 1
			except Exception as e:
				error = e
				failed += 1
			inv_item = frappe.get_doc(inv.doctype,inv.name)
			if error:
				inv.error_message = error
				inv_item.db_set("submission_status","Failed")
			else:
				inv_item.db_set("submission_status","Successful")
		if successful > failed :
			self.db_set("mr_invoice_submit",1)
	@frappe.whitelist()
	def post_to_account(self): 
		total_payable_amount = 0
		accounts = []
		bank_account = frappe.db.get_value("Branch",self.branch,"expense_bank_account")
		if not bank_account:
			bank_account = frappe.db.get_value("Company",self.company,"default_bank_account")
		for d in frappe.db.sql('''
				select name from `tabMR Employee Invoice` 
				where docstatus = 1 and mr_invoice_entry = '{}'
				and branch = '{}' and outstanding_amount > 0 
				'''.format(self.name, self.branch), as_dict=True):
				mr_invoice = frappe.get_doc("MR Employee Invoice",d.name)
				total_payable_amount += flt(mr_invoice.net_payable_amount,2)
				accounts.append({
					"account": mr_invoice.credit_account,
					"debit_in_account_currency": flt(mr_invoice.net_payable_amount,2),
					"cost_center": mr_invoice.cost_center,
					"party_check": 1,
					"party_type": "Muster Roll Employee",
					"party": mr_invoice.mr_employee,
					"party_name":mr_invoice.mr_employee_name,
					"reference_type": mr_invoice.doctype,
					"reference_name": mr_invoice.name,
				})
		accounts.append({
			"account": bank_account,
			"credit_in_account_currency": flt(total_payable_amount,2),
			"cost_center": self.cost_center
		})
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"naming_series": "Bank Payment Voucher",
			"title": "MR Employee Invoice Payment ",
			"user_remark": "Note: MR Employee Invoice Payment of {} for year {}".format(self.month, self.fiscal_year),
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(total_payable_amount),
			"branch": self.branch,
			"reference_type":self.doctype,
			"referece_doctype":self.name,
			"accounts":accounts
		})
		je.insert()
		frappe.msgprint(_('Journal Entry {0} posted to accounts').format(frappe.get_desk_link("Journal Entry",je.name)))

	@frappe.whitelist()
	def get_mr_employee(self):
		if not self.branch or not self.month or not self.fiscal_year:
			frappe.throw("Either Branch/Month/Fiscal Year is missing")
		self.set("items",[])
		for e in frappe.db.sql('''select 
									name as mr_employee, person_name as mr_employee_name 
									from `tabMuster Roll Employee` where status = 'Active'
									and branch = {}
									'''.format(frappe.db.escape(self.branch)), as_dict=True):
			self.append("items",e)

	@frappe.whitelist()
	def create_mr_invoice(self):
		self.check_permission('write')
		# self.created = 1
		args = frappe._dict({
			"mr_invoice_entry":self.name,
			"doctype":"MR Employee Invoice",
			"branch":self.branch,
			"cost_center":self.cost_center,
			"posting_date":self.posting_date,
			"company":self.company,
			"status":"Draft",
			"fiscal_year":self.fiscal_year,
			"month":self.month,
			"currency":self.currency,
			"credit_account":self.credit_account
		})
		failed = successful = 0
		for item in self.items:
			args.update({
				"mr_employee":item.mr_employee,
				"mr_employee_name": item.mr_employee_name,
				})
			error = None
			try:
				mr_invoice = frappe.get_doc(args)
				mr_invoice.get_ot()
				mr_invoice.get_attendance()
				mr_invoice.set("deduction",[])
				for d in self.deductions:
					if d.mr_employee == item.mr_employee:
						mr_invoice.append("deduction",{
							"account":d.account,
							"amount":d.amount,
							"remarks":d.remarks
						})
				mr_invoice.save()
				item.total_days_worked = mr_invoice.total_days_worked
				item.total_daily_wage_amount = mr_invoice.total_daily_wage_amount 
				item.other_deduction = mr_invoice.other_deduction
				item.net_payable_amount = mr_invoice.net_payable_amount
				item.total_ot_hrs = mr_invoice.total_ot_hrs
				item.total_ot_amount = mr_invoice.total_ot_amount
				item.grand_total = mr_invoice.grand_total
				item.reference = mr_invoice.name
				successful += 1
			except Exception as e:
				error = str(e)
				failed += 1

			item_invoic = frappe.get_doc(item.doctype,item.name)
			if error:
				item.creation_status ="Failed"
				item.error_message=error
			else:
				item.creation_status="Successful"
		if successful > failed:
			self.mr_invoice_created = 1
		self.save()
		self.reload()