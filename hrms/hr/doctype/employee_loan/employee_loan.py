# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta
import calendar
from frappe.utils import flt
from frappe.utils import flt, money_in_words, now_datetime, nowdate, getdate
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states

from frappe.model.document import Document

class EmployeeLoan(Document):
	def validate(self):
		self.validate_employment_status()
		self.validate_loan_amount()
		validate_workflow_states(self)

	def on_submit(self):
		self.post_journal_entry()
		self.update_salary_structure()

	def on_cancel(self):
		self.update_salary_structure(cancel=True)

	def validate_loan_amount(self):
		net_pay = frappe.db.sql(
			"""
			SELECT SUM(net_pay)
			FROM `tabSalary Structure`
			WHERE employee = '{}'
			AND is_active = "Yes"
		""".format(
				self.employee
			)
		)[0][0]
		if flt(self.monthly_deduction) > flt(net_pay):
			frappe.throw("Monthly deduction <strong>Nu. {}</strong> cannot be more than net pay <strong>Nu. {}</strong>".format(self.monthly_deduction, net_pay))

	@frappe.whitelist()
	def validate_employment_status(self):
		employment_type = frappe.db.get_value("Employee", self.employee, "employment_status")
		if employment_type == "Probation":
			frappe.throw(
				"Employee {}({}) who is in Probation Period is not eligible for Employee Loan."
			)

	def update_salary_structure(self, cancel=False):
		doc = frappe.get_doc("Salary Structure", {"employee": self.employee, "is_active": "Yes"})
		if cancel:
			rem_list = []
			for d in doc.get("deductions"):
				if d.salary_component == "Employee Loan" and self.name in (
					d.reference_number,
					d.ref_docname,
				):
					rem_list.append(d)

			[doc.remove(d) for d in rem_list]
			doc.save(ignore_permissions=True)
		else:
			if frappe.db.exists("Salary Structure", {"employee": self.employee, "is_active": "Yes"}):
				row = doc.append("deductions", {})
				row.salary_component = "Employee Loan"
				row.from_date = self.recovery_start_date
				row.to_date = self.recovery_end_date
				row.amount = flt(self.monthly_deduction)
				row.default_amount = flt(self.monthly_deduction)
				row.reference_number = self.name
				row.ref_docname = self.name
				row.total_deductible_amount = flt(self.loan_amount)
				row.total_deducted_amount = 0
				row.total_outstanding_amount = flt(self.loan_amount)
				row.total_days_in_month = 0
				row.working_days = 0
				row.leave_without_pay = 0
				row.payment_days = 0
				doc.save(ignore_permissions=True)
				# self.db_set("salary_structure", doc.name)
			else:
				frappe.throw(
					_("No active salary structure found for employee {0} {1}").format(
						self.employee, self.employee_name
					),
					title="No Data Found",
				)

	def post_journal_entry(self):
		je = frappe.new_doc("Journal Entry")
		je.posting_date = self.posting_date
		je.voucher_type = "Bank Entry"
		je.naming_series = "Bank Payment Voucher"
		je.company = self.company
		je.branch = self.branch
		je.remark = "Payment against Employee Advance: " + self.purpose

		loan_account = frappe.db.get_value("Company", self.company, "employee_loan_account")
		if not loan_account:
			frappe.throw("Please set employee loan account in {}".format(frappe.get_desk_link("Company", self.company)))
		bank_account = frappe.db.get_value("Company", self.company, "default_bank_account")
		if not bank_account:
			frappe.throw("Please set default bank account in {}".format(frappe.get_desk_link("Company", self.company)))
		je.append(
			"accounts",
			{
				"account": loan_account,
				"debit_in_account_currency": flt(self.loan_amount),
				"debit": flt(self.loan_amount),
				"reference_type": self.doctype,
				"reference_name": self.name,
				"party_type": "Employee",
				"party": self.employee,
				"cost_center": self.cost_center,
				"is_advance": "Yes",
			},
		)
		je.append(
			"accounts",
			{
				"account": bank_account,
				"cost_center": self.cost_center,
				"credit_in_account_currency": flt(self.loan_amount),
				"credit": flt(self.loan_amount),
			},
		)
		je.flags.ignore_permissions = 1
		je.insert()
		self.db_set("journal_entry", je.name)
		self.db_set(
			"journal_entry_status",
			"Forwarded to accounts for processing payment on {0}".format(
				now_datetime().strftime("%Y-%m-%d %H:%M:%S")
			),
		)
		frappe.msgprint(
			_("{} posted to accounts").format(frappe.get_desk_link(je.doctype, je.name))
		)

@frappe.whitelist()
def calculate_recovery_end_date(start_date, months):
	start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%m-%Y")
	start_date = datetime.strptime(start_date, "%d-%m-%Y")
	end_date = start_date + timedelta(days=int(months) * 30)
	_, last_day = calendar.monthrange(end_date.year, end_date.month)
	end_date = end_date.replace(day=last_day)
	end_date_str = end_date.strftime("%Y-%m-%d")
	return end_date_str