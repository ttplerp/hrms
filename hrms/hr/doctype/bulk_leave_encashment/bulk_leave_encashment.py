# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, flt, today, money_in_words, cint
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on
from hrms.payroll.doctype.salary_structure.salary_structure import get_basic_and_gross_pay
from hrms.hr.hr_custom_functions import get_salary_tax
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from erpnext.accounts.doctype.accounts_settings.accounts_settings import get_bank_account
from datetime import *

class BulkLeaveEncashment(Document):
	def validate(self):
		# validate_workflow_states(self)
		if not self.encashment_date:
			self.encashment_date = getdate(nowdate())
		self.get_leave_details_for_encashment()
		self.calculate_amount()
		# notify_workflow_states(self)

	def on_submit(self):
		self.update_encashed_in_leave_allocation()
		self.create_leave_ledger_entry()
		self.post_accounts_entry()
		# notify_workflow_states(self)

	def on_cancel(self):
		self.update_encashed_in_leave_allocation(cancel=1)
		self.create_leave_ledger_entry(submit=False)
		# notify_workflow_states(self)
	
	def calculate_amount(self):
		total_encashment_amount = net_payable = 0
		for d in self.items:
			total_encashment_amount += d.encashment_amount
			net_payable += d.payable_amount
		
		self.total_encashment_amount = flt(total_encashment_amount,2)
		self.net_payable_amount = flt(net_payable,2)
	
	def update_encashed_in_leave_allocation(self, cancel=0):
		if cint(cancel) == 0:
			for d in self.items:
				frappe.db.set_value("Leave Allocation", d.leave_allocation, "total_leaves_encashed",
					frappe.db.get_value('Leave Allocation', d.leave_allocation, 'total_leaves_encashed') + d.encashable_days)
		else:
			for d in self.items:
				frappe.db.set_value("Leave Allocation", d.leave_allocation, "total_leaves_encashed",
					frappe.db.get_value('Leave Allocation', d.leave_allocation, 'total_leaves_encashed') - d.encashable_days)

	def create_leave_ledger_entry(self, submit=True):
		for d in self.items:
			args = frappe._dict(
				employee=d.employee,
				employee_name=d.employee_name,
				leaves=d.encashable_days * -1,
				from_date=self.encashment_date,
				to_date=self.encashment_date,
				is_carry_forward=0
			)
			create_leave_ledger_entry(self, args, submit)

	def get_leave_details_for_encashment(self):
		if not frappe.db.get_value("Leave Type", self.leave_type, 'allow_encashment'):
			frappe.throw(_("Leave Type {0} is not encashable").format(self.leave_type))

		for emp in self.items:
			allocation = self.get_leave_allocation(emp.employee)

			if not allocation:
				frappe.throw(_("No Leaves Allocated to Employee: {0} for Leave Type: {1}").format(emp.employee, self.leave_type))

			emp.leave_balance = get_leave_balance_on(employee=emp.employee, date=today(), \
				to_date=today(), leave_type=self.leave_type, consider_all_leaves_in_the_allocation_period=True)

			if not emp.employee_group:
				emp.employee_group = frappe.db.get_value("Employee", emp.employee, "employee_group")
			
			emp.encashable_days = emp.leave_balance 

			if emp.encashable_days > emp.leave_balance:
				frappe.throw("Encashable Days  cannot be more than Leave Balance")

			pay = get_basic_and_gross_pay(employee=emp.employee, effective_date=today())
			if pay.get("basic_pay") is not None:
				emp.current_basic_pay = pay.get("basic_pay")
				emp.encashment_amount = flt((pay.get("basic_pay")/30) * flt(emp.encashable_days),2)
				emp.salary_structure = pay.get("name")
				emp.encashment_tax = get_salary_tax(emp.encashment_amount)
				emp.payable_amount = flt((emp.encashment_amount) - flt(emp.encashment_tax),2)

			emp.leave_allocation = allocation.name
		return True
	
	def get_leave_allocation(self, employee=None):
		leave_allocation = frappe.db.sql("""select name, to_date, total_leaves_allocated, carry_forwarded_leaves_count from `tabLeave Allocation` where '{0}'
		between from_date and to_date and docstatus=1 and leave_type='{1}'
		and employee = '{2}'""".format(self.encashment_date or getdate(nowdate()), self.leave_type, employee), as_dict=1)
		return leave_allocation[0] if leave_allocation else None
	
	@frappe.whitelist()
	def get_employees(self):
		if not self.leave_period or not self.leave_type:
			frappe.throw("Either Leave Type/Leave Period is missing")
		self.set('items', [])
		query = """
				select name as employee, employee_name, branch, designation, employment_type, grade,
				employee_group, bank_name, bank_ac_no
				from `tabEmployee` where status = 'Active'
		"""
		
		entries = frappe.db.sql(query, as_dict=True)
		self.set('items', entries)
	
	def post_accounts_entry(self):
		if not self.cost_center:
			frappe.throw("Setup Cost Center for employee in Employee Information")

		expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		if not expense_bank_account:
			frappe.throw("Setup Default Expense Bank Account for your Branch")

		expense_account = frappe.db.get_value("Company",self.company, "leave_encashment_account")
		if not expense_account:
			frappe.throw("Setup Leave Encashment Account in HR Accounts Settings")

		tax_account = frappe.db.get_value("Company",self.company, "salary_tax_account")
		if not tax_account:
			frappe.throw("Setup Tax Account in HR Accounts Settings")
		
		default_bank_account = get_bank_account(self.branch)
		default_payable_account = frappe.db.get_value("Company",self.company, "salary_payable_account")
		company_cc              = frappe.db.get_value("Company", self.company,"company_cost_center")

		cc = {}
		encashment_tax = net_payable = 0 
		for det in self.items:
			encashment_tax += det.encashment_tax
			net_payable += det.payable_amount
			cost_center = frappe.db.get_value("Branch", det.branch, "cost_center")
			if cost_center not in cc:
				cc.update({
        			cost_center: {
               			"payable_amount": det.payable_amount,
               			"encashment_amount": det.encashment_amount,
               			"encashment_tax": det.encashment_tax,
                    }
           		})
			else:
				cc[cost_center]['payable_amount'] += det.payable_amount
				cc[cost_center]['encashment_amount'] += det.encashment_amount
				cc[cost_center]['encashment_tax'] += det.encashment_tax
		
		#Payables Journal Entry -----------------------------------------------
		payables_je = frappe.new_doc("Journal Entry")
		payables_je.voucher_type= "Journal Entry"
		payables_je.naming_series = "Journal Voucher"
		payables_je.title = "Bulk Leave Encashment "+str(self.fiscal_year)+" - To Payables"
		payables_je.remark =  "Bulk Leave Encashment "+str(self.fiscal_year)+" - To Payables"
		payables_je.posting_date = self.encashment_date               
		payables_je.company = self.company
		payables_je.branch = self.branch
		payables_je.reference_type = self.doctype
		payables_je.reference_name =  self.name
		total = total_allowance = 0
		for rec in cc:
			payables_je.append("accounts", {
					"account": expense_account,
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": rec,
					"business_activity": self.business_activity,
					"debit_in_account_currency": flt(cc[rec]['encashment_amount'],2),
					"debit": flt(cc[rec]['encashment_amount'],2),
				})
		#Salary Tax
		if encashment_tax > 0:
			payables_je.append("accounts", {
					"account": tax_account,
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": company_cc,
					"business_activity": self.business_activity,
					"credit_in_account_currency": flt(encashment_tax,2),
					"party_check": 0,
					"credit": flt(encashment_tax,2),
				})
		#Salary Payble
		payables_je.append("accounts", {
				"account": default_payable_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"business_activity": self.business_activity,
				"credit_in_account_currency": flt(net_payable,2),
				"credit": flt(net_payable,2),
				"party_check": 0
			})

		payables_je.flags.ignore_permissions = 1
		payables_je.insert()
		# payables_je.submit()
		
		#Payables JE End -----------------------------------------------------
		sthc_je = frappe.new_doc("Journal Entry")
		sthc_je.voucher_type= "Bank Entry"
		sthc_je.naming_series = "Bank Payment Voucher"
		sthc_je.title = "Bulk Leave Encashment Tax for "+ self.fiscal_year
		sthc_je.remark =  "Bulk Leave Encashment Tax for "+self.fiscal_year
		sthc_je.posting_date = self.encashment_date            
		sthc_je.company = self.company
		sthc_je.branch = self.branch
		sthc_je.reference_type = self.doctype
		sthc_je.reference_name =  self.name
		#Salary Tax
		if encashment_tax > 0:
			sthc_je.append("accounts", {
					"account": frappe.db.get_value("Salary Component", "Salary Tax", "gl_head"),
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": company_cc,
					"business_activity": self.business_activity,
					"debit_in_account_currency": flt(encashment_tax,2),
					"debit": flt(encashment_tax,2),
					"party_check": 0
				})
		#To Bank Account
		sthc_je.append("accounts", {
				"account": default_bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"business_activity": self.business_activity,
				"credit_in_account_currency": flt(encashment_tax,2),
				"credit": flt(encashment_tax,2),
			})

		sthc_je.flags.ignore_permissions = 1 
		sthc_je.insert()

		#Payables to Bank Entry -----------------------------------------------
		pb_je = frappe.new_doc("Journal Entry")
		pb_je.voucher_type= "Bank Entry"
		pb_je.naming_series = "Bank Payment Voucher"
		pb_je.title = "Bulk Leave Encashment for the fiscal year of "+self.fiscal_year
		pb_je.remark = "Bulk Leave Encashment for the fiscal year of "+self.fiscal_year
		pb_je.posting_date = self.encashment_date               
		pb_je.company = self.company
		pb_je.branch = self.branch
		pb_je.reference_type = self.doctype
		pb_je.reference_name =  self.name
		#Salary Payable
		pb_je.append("accounts", {
				"account": default_payable_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"business_activity": self.business_activity,
				"debit_in_account_currency": flt(net_payable,2),
				"debit": flt(net_payable,2),
				"party_check": 0
			})
		#To Bank Account
		pb_je.append("accounts", {
				"account": default_bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"business_activity": self.business_activity,
				"credit_in_account_currency": flt(net_payable,2),
				"credit": flt(net_payable,2),
			})

		pb_je.flags.ignore_permissions = 1 
		pb_je.insert()
		self.db_set("journal_entries_created", 1)
		frappe.db.commit()
