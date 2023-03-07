# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt, nowdate, today, cint, get_last_day, month_diff, get_year_start
from frappe.utils import add_months,get_year_ending, datetime, getdate, get_first_day, math, ceil
import erpnext
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
from hrms.payroll.doctype.salary_structure.salary_structure import get_basic_and_gross_pay, get_salary_tax
from hrms.hr.utils import validate_active_employee
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states


class EmployeeAdvanceOverPayment(frappe.ValidationError):
	pass


class EmployeeAdvance(Document):
	def onload(self):
		self.get("__onload").make_payment_via_journal_entry = frappe.db.get_single_value(
			"Accounts Settings", "make_payment_via_journal_entry"
		)
	def validate(self):
		validate_workflow_states(self)
		validate_active_employee(self.employee)
		self.validate_employment_status()
		self.set_status()
		if self.advance_type != "Travel Advance" and self.advance_type != "Imprest Advance" :
			self.validate_advance_amount()
			self.validate_deduction_month()
		self.update_defaults()
		self.update_pending_amount()
		self.update_reference()
		self.check_duplicate_advance()
		self.select_advance_account()
		if self.workflow_state != "Approved":
			notify_workflow_states(self)
	
	def on_cancel(self):
		self.ignore_linked_doctypes = "GL Entry"
		self.set_status(update=True)
		self.update_travel_request()
		self.update_reference(cancel = 1)
		self.update_salary_structure(True)
	def on_submit(self):
		if self.advance_type =="Travel Advance":
			self.update_travel_request()
		if self.advance_type =="Salary Advance":
			self.update_salary_structure()
		self.make_bank_entry()
		notify_workflow_states(self)

	def select_advance_account(self):
		if self.advance_type == "Salary Advance":
			self.advance_account = frappe.db.get_value("Company", self.company, "salary_advance_account")
		elif self.advance_type == "Travel Advance":
			self.advance_account = frappe.db.get_value("Company", self.company, "travel_advance_account")
		elif self.advance_type == "Imprest Advance":
			self.advance_account = frappe.db.get_value("Company", self.company, "imprest_advance_account")
		else:
			account = ""
			
	def update_defaults(self):
		self.salary_component = "Salary Advance Deductions"
		
	def update_pending_amount(self):
		self.pending_amount = self.advance_amount

	def update_reference(self, cancel = 0):
		if self.advance_type == "Travel Advance" and cancel == 0:
			if not frappe.db.get_value("Travel Request",self.reference,"employee_advance_reference") and self.status == "Paid":
				frappe.db.sql(""" 
					update `tabTravel Request`
					set employee_advance_reference = '{0}'
					where name = '{1}'
				""".format(self.name,self.reference))
		if cancel == 1 and self.advance_type == "Travel Advance":
			frappe.db.sql(""" 
					update `tabTravel Request`
					set employee_advance_reference = NULL
					where name = '{}'
				""".format(self.reference))

	@frappe.whitelist()
	def validate_employment_status(self):
		if self.advance_type == "Salary Advance":
			employment_type = frappe.db.get_value("Employee",self.employee,"employment_status")
			if employment_type == "Probation":
				frappe.throw("Employee {}({}) who is in Probation Period is not eligible for Salary Advance.")

	def check_duplicate_advance(self):
		if frappe.db.sql("""
				select count(reference) 
				from `tabEmployee Advance` 
				where reference = '{}'
				and name != '{}'
				and docstatus != 2
			""".format(self.reference, self.name))[0][0] >= 1 :
			frappe.throw("Advance for Travel Request '{}' is already created".format(self.name))

	def update_salary_structure(self, cancel=False):
		if cancel:
			rem_list = []
			if self.salary_structure:
				doc = frappe.get_doc("Salary Structure", self.salary_structure)
				for d in doc.get("deductions"):
					if d.salary_component == self.salary_component and self.name in (d.reference_number, d.ref_docname):
						rem_list.append(d)

				[doc.remove(d) for d in rem_list]
				doc.save(ignore_permissions=True)
		else:
			if frappe.db.exists("Salary Structure", {"employee": self.employee, "is_active": "Yes"}):
				doc = frappe.get_doc("Salary Structure", {"employee": self.employee, "is_active": "Yes"})
				row = doc.append("deductions",{})
				row.salary_component        = self.salary_component
				row.from_date               = self.recovery_start_date
				row.to_date                 = self.recovery_end_date
				row.amount                  = flt(self.monthly_deduction)
				row.default_amount          = flt(self.monthly_deduction)
				row.reference_number        = self.name
				row.ref_docname             = self.name
				row.total_deductible_amount = flt(self.advance_amount)
				row.total_deducted_amount   = 0
				row.total_outstanding_amount= flt(self.advance_amount)
				row.total_days_in_month     = 0
				row.working_days            = 0
				row.leave_without_pay       = 0
				row.payment_days            = 0
				doc.save(ignore_permissions=True)
				self.db_set("salary_structure", doc.name)
			else:
				frappe.throw(_("No active salary structure found for employee {0} {1}").format(self.employee, self.employee_name), title="No Data Found")

	@frappe.whitelist()
	def get_accumulated_advance_amount(self):
		year_start_date = get_year_start(today())
		acc = frappe.db.sql("""select sum(advance_amount)
					from `tabEmployee Advance` 
					where employee = '{0}'
					and docstatus !=2
					and name !='{1}'
					and posting_date between'{2}' and '{3}'
					and advance_type = '{4}'""".format(self.employee,self.name, year_start_date,self.recovery_end_date, self.advance_type))[0][0]
		self.total_advance = flt(acc)
		#and salary_component ='Salary Advance Deductions'
	@frappe.whitelist()
	def validate_advance_amount(self):
		self.recovery_start_date = get_first_day(today())
		self.recovery_end_date = get_year_ending(today())
		year_start_date = get_year_start(today())
		ssl = frappe.db.sql("""select name,docstatus,str_to_date(concat(yearmonth,"01"),"%Y%m%d") as salary_month
					from `tabSalary Slip`
					where employee = '{0}'
					and str_to_date(concat(yearmonth,"01"),"%Y%m%d") >= '{1}'
					and docstatus = 1
					order by yearmonth desc limit 1
		""".format(self.employee,str(self.recovery_start_date)),as_dict=True)

		for ss in ssl:
			self.recovery_start_date = add_months(str(ss.salary_month),1)

		max_month_allow_from_employee_group = frappe.db.sql("""select salary_advance_max_months from `tabEmployee Group` where name = '{}'""".format(self.employee_group))[0][0]

		pervious_advance = frappe.db.sql("""select sum(advance_amount)
					from `tabEmployee Advance` 
					where employee = '{0}'
					and docstatus !=2
					and name !='{1}'
					and advance_type = 'Salary Advance'
					and salary_component ='Salary Advance Deductions'
					and posting_date between'{2}' and '{3}' """.format(self.employee,self.name, year_start_date,self.recovery_end_date))[0][0]
	
		remaining_pay = (flt(self.basic_pay) * flt(max_month_allow_from_employee_group))- flt(pervious_advance) 
		if flt(self.advance_amount) <= 0:
			frappe.throw("Enter valid <b>Advance Amount</b>")
		elif flt(self.advance_amount) >= (flt(remaining_pay)+1):
			frappe.throw("<b>Advance Amount</b> should not be more than max amount limit")
		elif flt(pervious_advance) == (flt(self.basic_pay) * flt(max_month_allow_from_employee_group)):
			frappe.throw("Your <b>Salary Advance</b> was alrady claimed")
		else:
			self.max_no_of_installment = month_diff(self.recovery_end_date,self.recovery_start_date)
			check_advance = flt(self.advance_amount) / flt(self.deduction_month)
			if flt(self.advance_amount) > (flt(self.basic_pay) * flt(max_month_allow_from_employee_group)):
				frappe.throw("<b>Advance Amount</b> can not exced <b>Maximum Advance Limit</b> ")
			elif flt(check_advance) > flt(self.net_pay):
				frappe.throw("Your <b>Advance Amount</b> can not exced <b>Net Pay</b>")
			else:
				self.monthly_deduction = ceil(check_advance)

	@frappe.whitelist()
	def validate_deduction_month(self):
		self.recovery_start_date = get_first_day(today())
		self.recovery_end_date = get_year_ending(today())
		ssl = frappe.db.sql("""select name,docstatus,str_to_date(concat(yearmonth,"01"),"%Y%m%d") as salary_month
					from `tabSalary Slip`
					where employee = '{0}'
					and str_to_date(concat(yearmonth,"01"),"%Y%m%d") >= '{1}'
					and docstatus = 1
					order by yearmonth desc limit 1
		""".format(self.employee,str(self.recovery_start_date)),as_dict=True)

		for ss in ssl:
			self.recovery_start_date = add_months(str(ss.salary_month),1)

		self.max_no_of_installment = month_diff(self.recovery_end_date,self.recovery_start_date)

		if flt(self.deduction_month) > flt(self.max_no_of_installment):
			frappe.throw("<b>No.of Installment</b> can not exced  <b>{}</b>".format(self.max_no_of_installment))
		else:
			check_advance = flt(self.advance_amount) / flt(self.deduction_month)
			if flt(check_advance) > flt(self.net_pay):
				frappe.throw("Your <b>Advance Amount</b> can not exced <b>Net Pay</b>")
			else:
				self.monthly_deduction = ceil(flt(self.advance_amount)/ flt(self.deduction_month))
				date_change = self.max_no_of_installment - self.deduction_month
				self.recovery_end_date = add_months(str(self.recovery_end_date), - date_change)

	@frappe.whitelist()
	def	set_pay_details(self):
		pay = get_basic_and_gross_pay(employee=self.employee, effective_date=today())
		self.basic_pay = flt(pay.get("basic_pay"))
		self.net_pay = frappe.db.sql("""select sum(net_pay) 
			from `tabSalary Structure` 
			where employee = '{}' 
			and is_active = "Yes" """.format(self.employee))[0][0]
		self.recovery_start_date = get_first_day(today())
		self.recovery_end_date = get_year_ending(today())
		
		ssl = frappe.db.sql("""select name,docstatus,str_to_date(concat(yearmonth,"01"),"%Y%m%d") as salary_month
					from `tabSalary Slip`
					where employee = '{0}'
					and str_to_date(concat(yearmonth,"01"),"%Y%m%d") >= '{1}'
					and docstatus = 1
					order by yearmonth desc limit 1
		""".format(self.employee,str(self.recovery_start_date)),as_dict=True)
		for ss in ssl:
			self.recovery_start_date = add_months(str(ss.salary_month),1)

		self.max_no_of_installment = month_diff(self.recovery_end_date,self.recovery_start_date)
		self.deduction_month = self.max_no_of_installment
		self.max_months_limit = frappe.get_value("Employee Group", self.employee_group, "salary_advance_max_months")
		self.max_advance_limit = flt(self.max_months_limit) * flt(self.basic_pay)
		self.monthly_deduction = ceil(flt(self.advance_amount)/ flt(self.deduction_month))

	def update_travel_request(self):
		if self.reference_type == "Travel Request":
			doc = frappe.get_doc(self.reference_type,self.reference)
			if self.docstatus == 2:
				advance_amount = doc.advance_amount - flt(self.advance_amount)
				frappe.db.sql("""
					update `tabTravel Request` set need_advance = 0,
					advance_amount = {}
					where name = '{}'
				""".format(advance_amount, self.reference))
				if advance_amount != 0:
					frappe.throw("Advance Amount in Travel Request doesn't match with Advance Amount in Employee Advance")
			# doc.save(ignore_permissions=True)

	def set_status(self, update=False):
		precision = self.precision("paid_amount")
		total_amount = flt(flt(self.claimed_amount) + flt(self.return_amount), precision)
		status = None

		if self.docstatus == 0:
			status = "Draft"
		elif self.docstatus == 1:
			if flt(self.claimed_amount) > 0 and flt(self.claimed_amount, precision) == flt(
				self.paid_amount, precision
			):
				status = "Claimed"
			elif flt(self.return_amount) > 0 and flt(self.return_amount, precision) == flt(
				self.paid_amount, precision
			):
				status = "Returned"
			elif (
				flt(self.claimed_amount) > 0
				and (flt(self.return_amount) > 0)
				and total_amount == flt(self.paid_amount, precision)
			):
				status = "Partly Claimed and Returned"
			elif flt(self.paid_amount) > 0 and flt(self.advance_amount, precision) == flt(
				self.paid_amount, precision
			):
				status = "Paid"
			else:
				status = "Unpaid"
		elif self.docstatus == 2:
			status = "Cancelled"

		if update:
			self.db_set("status", status)
			if self.status == "Paid" and self.reference_type == "Travel Request":
				self.update_reference()
		else:
			self.status = status
			if self.status == "Paid" and self.reference_type == "Travel Request":
				self.update_reference()

	def set_total_advance_paid(self):
		gle = frappe.qb.DocType("GL Entry")

		paid_amount = (
			frappe.qb.from_(gle)
			.select(Sum(gle.debit).as_("paid_amount"))
			.where(
				(gle.against_voucher_type == "Employee Advance")
				& (gle.against_voucher == self.name)
				& (gle.party_type == "Employee")
				& (gle.party == self.employee)
				& (gle.docstatus == 1)
				& (gle.is_cancelled == 0)
			)
		).run(as_dict=True)[0].paid_amount or 0

		return_amount = (
			frappe.qb.from_(gle)
			.select(Sum(gle.credit).as_("return_amount"))
			.where(
				(gle.against_voucher_type == "Employee Advance")
				& (gle.voucher_type != "Expense Claim")
				& (gle.against_voucher == self.name)
				& (gle.party_type == "Employee")
				& (gle.party == self.employee)
				& (gle.docstatus == 1)
				& (gle.is_cancelled == 0)
			)
		).run(as_dict=True)[0].return_amount or 0

		if paid_amount != 0:
			paid_amount = flt(paid_amount) / flt(self.exchange_rate)
		if return_amount != 0:
			return_amount = flt(return_amount) / flt(self.exchange_rate)

		if flt(paid_amount) > self.advance_amount:
			frappe.throw(
				_("Row {0}# Paid Amount cannot be greater than requested advance amount"),
				EmployeeAdvanceOverPayment,
			)

		if flt(return_amount) > self.paid_amount - self.claimed_amount:
			frappe.throw(_("Return amount cannot be greater unclaimed amount"))

		self.db_set("paid_amount", paid_amount)
		self.db_set("return_amount", return_amount)
		self.set_status(update=True)

	def update_claimed_amount(self, cancel=0):
		claimed_amount = (
			frappe.db.sql(
				"""
			SELECT sum(ifnull(eca.allocated_amount, 0))
			FROM `tabExpense Claim Advance` eca, `tabExpense Claim` ec
			WHERE
				eca.employee_advance = %s
				AND ec.name = eca.parent
				AND ec.docstatus=1
				AND eca.allocated_amount > 0
		""",
				self.name,
			)[0][0]
			or 0
		)

		frappe.db.set_value("Employee Advance", self.name, "claimed_amount", flt(claimed_amount))

		# added by Dendup for imprest settlement
		if cint(cancel) == 0:
			if flt(self.paid_amount) == flt(claimed_amount):
				frappe.db.set_value("Employee Advance", self.name, "expenses_claimed", 1)
		else:
			frappe.db.set_value("Employee Advance", self.name, "expenses_claimed", 0)

		self.reload()
		self.set_status(update=True)

	def make_bank_entry(self):
		doc = frappe.get_doc(self.doctype, self.name)
		payment_account = get_default_bank_cash_account(
			doc.company, account_type="Cash", mode_of_payment=doc.mode_of_payment
		)
		if not payment_account:
			frappe.throw(_("Please set a Default Cash Account in Company defaults"))

		advance_account_currency = frappe.db.get_value("Account", doc.advance_account, "account_currency")

		advance_amount, advance_exchange_rate = get_advance_amount_advance_exchange_rate(
			advance_account_currency, doc
		)

		paying_amount, paying_exchange_rate = get_paying_amount_paying_exchange_rate(payment_account, doc)
		employee_cost_center = frappe.db.get_value("Branch",self.branch,"cost_center")
		default_payment_account = frappe.db.get_value("Company", self.company,"default_bank_account")
		if self.advance_type == "Salary Advance":
			account_select = frappe.db.get_value("Company", self.company,"salary_advance_account")
		elif self.advance_type == "Travel Advance":
			account_select = frappe.db.get_value("Company", self.company,"travel_advance_account")
		elif self.advance_type == "Imprest Advance":
			account_select = frappe.db.get_value("Company", self.company,"imprest_advance_account")
		else:
			frappe.throw("Choose different advance type")
		
		je = frappe.new_doc("Journal Entry")
		je.posting_date = nowdate()
		je.voucher_type = "Bank Entry"
		je.company = self.company
		je.branch = self.branch
		je.remark = "Payment against Employee Advance: " +  doc.purpose

		je.append(
			"accounts",
			{
				"account": account_select,
				"account_currency": advance_account_currency,
				"exchange_rate": flt(advance_exchange_rate),
				"debit_in_account_currency": flt(self.advance_amount),
				"reference_type": self.doctype,
				"reference_name": doc.name,
				"party_type": "Employee",
				"cost_center": employee_cost_center,
				"party": self.employee,
				"is_advance": "Yes",
			},
		)
		je.append(
			"accounts",
			{
				"account": default_payment_account,
				"cost_center": employee_cost_center,
				"credit_in_account_currency": flt(self.advance_amount),
				"account_currency": payment_account.account_currency,
				"exchange_rate": flt(paying_exchange_rate),
			},
		)
		je.flags.ignore_permissions=1
		je.insert()
		frappe.db.set_value(self.doctype, self.name, "je_reference", je.name)
		
@frappe.whitelist()
def get_pending_amount(employee, posting_date):
	employee_due_amount = frappe.get_all(
		"Employee Advance",
		filters={"employee": employee, "docstatus": 1, "posting_date": ("<=", posting_date)},
		fields=["advance_amount", "paid_amount"],
	)
	return sum([(emp.advance_amount - emp.paid_amount) for emp in employee_due_amount])


def get_advance_amount_advance_exchange_rate(advance_account_currency, doc):
	if advance_account_currency != doc.currency:
		advance_amount = flt(doc.advance_amount) * flt(doc.exchange_rate)
		advance_exchange_rate = 1
	else:
		advance_amount = doc.advance_amount
		advance_exchange_rate = doc.exchange_rate

	return advance_amount, advance_exchange_rate


def get_paying_amount_paying_exchange_rate(payment_account, doc):
	if payment_account.account_currency != doc.currency:
		paying_amount = flt(doc.advance_amount) * flt(doc.exchange_rate)
		paying_exchange_rate = 1
	else:
		paying_amount = doc.advance_amount
		paying_exchange_rate = doc.exchange_rate

	return paying_amount, paying_exchange_rate


@frappe.whitelist()
def create_return_through_additional_salary(doc):
	import json

	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))

	additional_salary = frappe.new_doc("Additional Salary")
	additional_salary.employee = doc.employee
	additional_salary.currency = doc.currency
	additional_salary.amount = doc.paid_amount - doc.claimed_amount
	additional_salary.company = doc.company
	additional_salary.ref_doctype = doc.doctype
	additional_salary.ref_docname = doc.name

	return additional_salary


@frappe.whitelist()
def make_return_entry(
	employee,
	company,
	employee_advance_name,
	return_amount,
	advance_account,
	currency,
	exchange_rate,
	mode_of_payment=None,
):
	bank_cash_account = get_default_bank_cash_account(
		company, account_type="Cash", mode_of_payment=mode_of_payment
	)
	if not bank_cash_account:
		frappe.throw(_("Please set a Default Cash Account in Company defaults"))

	advance_account_currency = frappe.db.get_value("Account", advance_account, "account_currency")

	je = frappe.new_doc("Journal Entry")
	je.posting_date = nowdate()
	je.voucher_type = get_voucher_type(mode_of_payment)
	je.company = company
	je.remark = "Return against Employee Advance: " + employee_advance_name
	je.multi_currency = 1 if advance_account_currency != bank_cash_account.account_currency else 0

	advance_account_amount = (
		flt(return_amount)
		if advance_account_currency == currency
		else flt(return_amount) * flt(exchange_rate)
	)

	je.append(
		"accounts",
		{
			"account": advance_account,
			"credit_in_account_currency": advance_account_amount,
			"account_currency": advance_account_currency,
			"exchange_rate": flt(exchange_rate) if advance_account_currency == currency else 1,
			"reference_type": "Employee Advance",
			"reference_name": employee_advance_name,
			"party_type": "Employee",
			"party": employee,
			"is_advance": "Yes",
			"cost_center": erpnext.get_default_cost_center(company),
		},
	)

	bank_amount = (
		flt(return_amount)
		if bank_cash_account.account_currency == currency
		else flt(return_amount) * flt(exchange_rate)
	)

	je.append(
		"accounts",
		{
			"account": bank_cash_account.account,
			"debit_in_account_currency": bank_amount,
			"account_currency": bank_cash_account.account_currency,
			"account_type": bank_cash_account.account_type,
			"exchange_rate": flt(exchange_rate) if bank_cash_account.account_currency == currency else 1,
			"cost_center": erpnext.get_default_cost_center(company),
		},
	)

	return je.as_dict()


def get_voucher_type(mode_of_payment=None):
	voucher_type = "Cash Entry"

	if mode_of_payment:
		mode_of_payment_type = frappe.get_cached_value("Mode of Payment", mode_of_payment, "type")
		if mode_of_payment_type == "Bank":
			voucher_type = "Bank Entry"

	return voucher_type
@frappe.whitelist()
def select_account(advance_type, company):
	if advance_type == "Salary Advance":
		account = frappe.db.get_value("Company", company, "salary_advance_account")
	elif advance_type == "Travel Advance":
		account = frappe.db.get_value("Company", company, "travel_advance_account")
	elif advance_type == "Imprest Advance":
		account = frappe.db.get_value("Company", company, "imprest_advance_account")
	else:
		account = ""
	return account

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles or "Accounts User" in user_roles or "System Manager" in user_roles:
		return

	return """(
		`tabEmployee Advance`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabEmployee Advance`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabEmployee Advance`.advance_approver_name = '{user}' and `tabEmployee Advance`.workflow_state not in  ('Draft','Approved','Rejected','Cancelled'))
	)""".format(user=user)
