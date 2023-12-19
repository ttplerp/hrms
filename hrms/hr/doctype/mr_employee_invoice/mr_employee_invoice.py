# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.custom_utils import check_future_date
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
from erpnext.accounts.general_ledger import (
	get_round_off_account_and_cost_center,
	make_gl_entries,
	make_reverse_gl_entries,
	merge_similar_entries,
)
from frappe import _, qb, throw, msgprint
from erpnext.controllers.accounts_controller import AccountsController

class MREmployeeInvoice(AccountsController):
	def validate(self):
		check_future_date(self.posting_date)
		self.calculate_amount()
		self.set_status()

	def calculate_amount(self):
		grand_total = outstanding_amount = other_deductions = net_payable = total_ot_amount = total_daily_wage_amount = 0
		for a in self.attendance:
			if cint(a.is_lumpsum) == 0:
				total_daily_wage_amount += flt(a.daily_wage,2)
			else:
				total_daily_wage_amount = flt(a.daily_wage,2)	 
		for a in self.ot:
			total_ot_amount += flt(a.amount,2)
		for d in self.deduction:
			other_deductions += flt(d.amount,2)
		self.other_deduction = flt(other_deductions,2)
		self.total_ot_amount = flt(total_ot_amount,2)
		self.total_daily_wage_amount = flt(total_daily_wage_amount,2)
		self.grand_total = flt(total_daily_wage_amount + total_ot_amount,2)
		self.outstanding_amount = self.net_payable_amount = flt(self.grand_total - self.other_deduction,2)
		
	def on_submit(self):
		self.make_gl_entries()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")
		self.make_gl_entries()
		
	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			self.payment_status = "Draft"
			return

		outstanding_amount = flt(self.outstanding_amount, 2)
		if not status:
			if self.docstatus == 2:
				payment_status = "Cancelled"
			elif self.docstatus == 1:
				if outstanding_amount > 0 and flt(self.net_payable_amount) > outstanding_amount:
					self.payment_status = "Partly Paid"
				elif outstanding_amount > 0 :
					self.payment_status = "Unpaid"
				elif outstanding_amount <= 0:
					self.payment_status = "Paid"
				else:
					self.payment_status = "Submitted"
			else:
				self.payment_status = "Draft"

		if update:
			self.db_set("payment_status", self.payment_status, update_modified=update_modified)

	def make_gl_entries(self):
		gl_entries = []
		self.make_party_gl_entry(gl_entries)
		self.deduction_gl_entries(gl_entries)
		self.expense_gl_entries(gl_entries)
		gl_entries = merge_similar_entries(gl_entries)
		make_gl_entries(gl_entries,update_outstanding="No",cancel=self.docstatus == 2)

	def expense_gl_entries(self, gl_entries):
		ot_account = frappe.db.get_value("Company",self.company,"mr_ot_account")
		wages_account = frappe.db.get_value("Branch",self.branch,"muster_roll_expense_account")
		if not ot_account:
			frappe.throw("MR Overtime Accountis missing in company")
		if not wages_account:
			frappe.throw("MR Wage Account is missing in branch <b>{}</b>".format(self.branch))
		gl_entries.append(
			self.get_gl_dict({
					"account":  wages_account,
					"debit": flt(self.total_daily_wage_amount,2),
					"debit_in_account_currency": flt(self.total_daily_wage_amount,2),
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"party_type": "Muster Roll Employee",
					"party": self.mr_employee,
					"cost_center": self.cost_center,
					"voucher_type":self.doctype,
					"voucher_no":self.name,
					"project":self.project
			}, self.currency)
		)
		gl_entries.append(
			self.get_gl_dict({
					"account":  ot_account,
					"debit": flt(self.total_ot_amount,2),
					"debit_in_account_currency": flt(self.total_ot_amount,2),
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"party_type": "Muster Roll Employee",
					"party": self.mr_employee,
					"cost_center": self.cost_center,
					"voucher_type":self.doctype,
					"voucher_no":self.name,
					"project":self.project
			}, self.currency)
		)
	def make_party_gl_entry(self, gl_entries):
		if flt(self.net_payable_amount) > 0:
			# Did not use base_grand_total to book rounding loss gle
			gl_entries.append(
				self.get_gl_dict({
					"account": self.credit_account,
					"credit": flt(self.net_payable_amount,2),
					"credit_in_account_currency": flt(self.net_payable_amount,2),
					"against_voucher": self.name,
					"party_type": "Muster Roll Employee",
					"party": self.mr_employee,
					"against_voucher_type": self.doctype,
					"cost_center": self.cost_center,
					"voucher_type":self.doctype,
					"voucher_no":self.name,
					"project":self.project
				}, self.currency))
	
	def deduction_gl_entries(self,gl_entries):
		for d in self.deduction:
			gl_entries.append(
				self.get_gl_dict({
					"account":  d.account,
					"credit": flt(d.amount,2),
					"credit_in_account_currency": flt(d.amount,2),
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"party_type": "Muster Roll Employee",
					"party": self.mr_employee,
					"cost_center": self.cost_center,
					"voucher_type":self.doctype,
					"voucher_no":self.name,
					"project":self.project
				}, self.currency)
			)
	@frappe.whitelist()
	def get_attendance(self):
		if not self.mr_employee or not self.fiscal_year or not self.month or not self.mr_employee:
			frappe.msgprint("MR Employee or Fiscal Year or Month is missing",raise_exception=True)
		month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(self.month) + 1
		month = str(month) if cint(month) > 9 else str("0" + str(month))
		start_date = getdate(str(self.fiscal_year)+"-"+str(month)+"-01")
		end_date = get_last_day(start_date)
		self.total_days_worked = 0
		self.set("attendance",[])
		for d in frappe.db.sql('''
				select a.name as mr_attendance, a.status,
					a.date, b.is_lumpsum, 
					CASE
						WHEN b.is_lumpsum = 1 THEN b.lumpsum
						ELSE b.rate_per_day
					END AS daily_wage
				from `tabMuster Roll Attendance` a join
				`tabMuster Roll Employee` b on a.mr_employee = b.name
				where a.date between '{}' and '{}' and a.status = 'Present' 
				and a.docstatus = 1 and a.mr_employee = '{}'
				and not exists (select 1 from `tabMR Employee Invoice` e inner join `tabMR Attendance Item` f 
								on e.name = f.parent where e.name != '{}' and f.mr_attendance = a.name and e.docstatus != 2)
				'''.format(start_date, end_date, self.mr_employee, self.name), as_dict=1):
			self.total_days_worked += 1
			self.append("attendance", d)
		if len(self.attendance) <= 0:
			frappe.msgprint("No attendance found for year {} of month {}".format(frappe.bold(self.fiscal_year), frappe.bold(self.month)),raise_exception=True)

	@frappe.whitelist()
	def get_ot(self):
		if not self.mr_employee or not self.fiscal_year or not self.month or not self.mr_employee:
			frappe.throw("MR Employee or Fiscal Year or Month is missing")
		month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(self.month) + 1
		month = str(month) if cint(month) > 9 else str("0" + str(month))
		start_date = getdate(str(self.fiscal_year)+"-"+str(month)+"-01")
		end_date = get_last_day(start_date)
		self.total_ot_hrs = 0
		self.set("ot",[])
		for d in frappe.db.sql('''
				select a.name as overtime_entries, a.number_of_hours,
					a.date, b.rate_per_hour as ot_rate
				from `tabMuster Roll Overtime Entry` a join
				`tabMuster Roll Employee` b on a.mr_employee = b.name
				where a.date between '{}' and '{}' 
				and a.docstatus = 1 and a.mr_employee = '{}'
                and not exists(select 1 from `tabMR Employee Invoice` c inner join `tabOvertime Invoice Item` d
                 on c.name = d.parent where c.docstatus != 2 and c.name != '{}' and d.overtime_entries = a.name )
				'''.format(start_date, end_date, self.mr_employee, self.name), as_dict=1):
			self.total_ot_hrs += flt(d.number_of_hours)
			d.update({"amount": flt(flt(d.ot_rate) * flt(d.number_of_hours),2)})
			self.append("ot",d)
		if len(self.ot) <= 0:
			frappe.msgprint("No OT found for year {} of month {}".format(frappe.bold(self.fiscal_year), frappe.bold(self.month)),raise_exception=False)
	
	@frappe.whitelist()
	def post_journal_entry(self):
		if self.journal_entry and frappe.db.exists("Journal Entry",{"name":self.journal_entry,"docstatus":("!=",2)}):
			frappe.msgprint(_("Journal Entry Already Exists {}".format(frappe.get_desk_link("Journal Entry",self.journal_entry))))
		if not self.net_payable_amount:
			frappe.throw(_("Payable Amount should be greater than zero"))
			
		credit_account = self.credit_account
	
		if not credit_account:
			frappe.throw("Expense Account is mandatory")
		r = []
		if self.remarks:
			r.append(_("Note: {0}").format(self.remarks))

		remarks = ("").join(r) #User Remarks is not mandatory
		bank_account = frappe.db.get_value("Branch",self.branch, "expense_bank_account")
		if not bank_account:
			frappe.throw(_("Default bank account is not set in company {}".format(frappe.bold(self.company))))
		# Posting Journal Entry
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"naming_series": "Bank Payment Voucher",
			"title": "Muster Roll Employee "+ self.mr_employee,
			"user_remark": "Note: " + "Muster Roll Employee Payment - " + self.mr_employee,
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.net_payable_amount),
			"branch": self.branch,
			"reference_type":self.doctype,
			"referece_doctype":self.name
		})
		je.append("accounts",{
			"account": credit_account,
			"debit_in_account_currency": self.net_payable_amount,
			"cost_center": self.cost_center,
			"party_check": 1,
			"party_type": "Muster Roll Employee",
			"party": self.mr_employee,
			"reference_type": self.doctype,
			"reference_name": self.name
		})
		je.append("accounts",{
			"account": bank_account,
			"credit_in_account_currency": self.net_payable_amount,
			"cost_center": self.cost_center
		})

		je.insert()
		#Set a reference to the claim journal entry
		self.db_set("journal_entry",je.name)
		frappe.msgprint(_('Journal Entry {0} posted to accounts').format(frappe.get_desk_link("Journal Entry",je.name)))
	