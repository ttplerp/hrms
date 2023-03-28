# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, money_in_words

class MPITransaction(Document):
	def validate(self):
		self.assign_account()
		self.calculate_total()

	def assign_account(self):
		self.mpi_expense_account = frappe.db.get_value("Salary Component",{"name":"MPI","enabled":1},"gl_head")
		self.payable_account = frappe.db.get_value("Company",self.company,"employee_payable_account")
		self.health_contribution_account = frappe.db.get_value("Salary Component",{"name":"Health Contribution","enabled":1},"gl_head")

	def on_submit(self):
		self.post_journal_entry()

	def post_journal_entry(self):
		bank_account = frappe.db.get_value("Company",self.company,"default_bank_account")
		if not self.net_amount:
			frappe.throw(_("Payable Amount should be greater than zero"))
		je = []
		je.append(self.create_payable_entry())
		je.append(self.be_health_contribution(bank_account))
		je.append(self.be_for_employee(bank_account))

	def be_for_employee(self,bank_account):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1

		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"title": "MPI Payment to Employee",
			"user_remark": "Note: MPI Payment to Employee",
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.net_amount),
			"branch": self.branch
		})
		for d in self.items:
			je.append("accounts",{
				"account": self.payable_account,
				"debit_in_account_currency": flt(d.net_mpi_amount,2),
				"cost_center": d.cost_center if d.cost_center else self.cost_center,
				"party_check": 1,
				"party_type": "Employee",
				"party": d.employee,
				"party_name": d.employee_name,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		je.append("accounts",{
			"account": bank_account,
			"credit_in_account_currency": flt(self.net_amount,2),
			"cost_center": self.cost_center
		})

		je.insert()
		return je.name

	def be_health_contribution(self,bank_account):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1

		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"title": "MPI Payment to Employee",
			"user_remark": "Note: MPI Payment to Employee",
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.total_deduction),
			"branch": self.branch
		})
		je.append("accounts",{
				"account": self.health_contribution_account,
				"debit_in_account_currency": flt(self.total_deduction,2),
				"cost_center": self.cost_center,
				"reference_type": self.doctype,
				"reference_name": self.name
			})

		je.append("accounts",{
			"account": bank_account,
			"credit_in_account_currency": flt(self.total_deduction,2),
			"cost_center": self.cost_center
		})

		je.insert()
		return je.name

	def create_payable_entry(self):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1

		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"title": "MPI Payment to Employee",
			"user_remark": "Note: MPI Payment to Employee",
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.total_mpi_amount),
			"branch": self.branch
		})
		for d in self.items:
			je.append("accounts",{
				"account": self.payable_account,
				"credit_in_account_currency": flt(d.net_mpi_amount,2),
				"cost_center": d.cost_center if d.cost_center else self.cost_center,
				"party_check": 1,
				"party_type": "Employee",
				"party": d.employee,
				"party_name": d.employee_name,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		je.append("accounts",{
				"account": self.health_contribution_account,
				"credit_in_account_currency": flt(self.total_deduction,2),
				"cost_center": self.cost_center,
				"reference_type": self.doctype,
				"reference_name": self.name
			})

		je.append("accounts",{
			"account": self.mpi_expense_account,
			"debit_in_account_currency": flt(self.total_mpi_amount,2),
			"cost_center": self.cost_center 
		})

		je.insert()
		return je.name

	def calculate_total(self):
		total_amount = total_mpi_amount = total_deduction = net_amount = 0
		for d in self.items:
			d.mpi_amount = flt(flt(d.gross_basic_pay) * flt(self.mpi_percent) / 100,2)
			d.deduction_amount = flt(flt(d.mpi_amount) * flt(self.deduction_percent)/ 100,0)
			d.net_mpi_amount = flt(flt(d.mpi_amount) - flt(d.deduction_amount),2)
			total_mpi_amount 	+= flt(d.mpi_amount,2)
			total_deduction 	+= flt(d.deduction_amount,0)
			total_amount       	+= flt(d.gross_basic_pay,2)
			net_amount 			+= flt(d.net_mpi_amount,2)

		self.total_amount 		= flt(total_amount,2)
		self.total_mpi_amount 	= flt(total_mpi_amount,2)
		self.total_deduction 	= flt(total_deduction,0)
		self.net_amount 		= flt(net_amount,2)

	@frappe.whitelist()
	def get_mpi_details(self):
		if not self.fiscal_year:
			frappe.throw("Fiscal Year is Mandatory")
		if flt(self.mpi_percent) <= 0 :
			frappe.throw("MPI percent cannot be 0 or less than 0")
		self.set("items",[])
		total_amount = total_mpi_amount = total_deduction = net_amount = 0
		for d in frappe.db.sql('''
				SELECT e.name as employee, e.employee_name,
						e.branch, e.cost_center, e.designation,
						e.date_of_joining, 
						(CASE WHEN e.employment_type = 'Contract' 
							THEN e.contract_end_date ELSE e.date_of_retirement END) as relieving_date,
						ss.name as salary_structure
				FROM `tabEmployee` e, `tabSalary Structure` ss 
				WHERE ss.eligible_for_mpi = 1 AND ss.employee = e.name and ss.docstatus = 0
				''',as_dict=True):
			basic_pay = frappe.db.sql('''
				SELECT sd.amount, SUM(sd.amount)
				FROM `tabSalary Slip` ss, `tabSalary Detail` sd 
				WHERE sd.parent = ss.name
				AND sd.salary_component = 'Basic Pay' AND ss.fiscal_year = '{fiscal_year}'
				AND ss.salary_structure = '{salary_structure}' 
				AND ss.employee = '{employee}' AND ss.docstatus = 1
			'''.format(fiscal_year = self.fiscal_year, salary_structure = d.salary_structure, employee = d.employee))
			working_days =  frappe.db.sql('''
				SELECT SUM(ssi.working_days)
				FROM `tabSalary Slip` ss, `tabSalary Slip Item` ssi
				WHERE ssi.parent = ss.name 	
				AND ss.fiscal_year = '{fiscal_year}' AND ss.salary_structure = '{salary_structure}'
				AND ss.employee = '{employee}' AND ss.docstatus = 1
			'''.format(fiscal_year = self.fiscal_year, salary_structure = d.salary_structure, employee = d.employee))
			if basic_pay[0][0] and basic_pay[0][1] and working_days[0][0]:
				d.update({
					"basic_pay":basic_pay[0][0],
					"gross_basic_pay":basic_pay[0][1],
					"total_days_worked":working_days[0][0]
				})
				mpi_amount = flt(flt(d.gross_basic_pay) * flt(self.mpi_percent) / 100,2)
				deduction_amount = flt(flt(mpi_amount) * flt(self.deduction_percent)/ 100,0)
				net_mpi_amount = flt(flt(mpi_amount) - flt(deduction_amount),2)
				d.update({
					"mpi_amount":flt(mpi_amount,2),
					"deduction_amount":flt(deduction_amount,0),
					"net_mpi_amount":flt(net_mpi_amount,2)
				})
				total_mpi_amount 	+= flt(mpi_amount,2)
				total_deduction 	+= flt(deduction_amount,0)
				total_amount       	+= flt(d.gross_basic_pay,2)
				net_amount 			+= flt(d.net_mpi_amount,2)

			self.append("items",d)
		self.total_amount 		= flt(total_amount,2)
		self.total_mpi_amount 	= flt(total_mpi_amount,2)
		self.total_deduction 	= flt(total_deduction,2)
		self.net_amount 		= flt(net_amount, 2)

			

