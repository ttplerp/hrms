# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, money_in_words
from collections import defaultdict
class MPITransaction(Document):
	def validate(self):
		self.assign_account()
		self.calculate_total()

	def assign_account(self):
		self.mpi_expense_account = frappe.db.get_value("Salary Component",{"name":"MPI","enabled":1},"gl_head")
		self.payable_account =  frappe.db.get_value("Company", self.company,"employee_payable_account")
		self.health_contribution_account = frappe.db.get_value("Salary Component",{"name":"Health Contribution","enabled":1},"gl_head")

	def on_submit(self):
		self.post_journal_entry()
	
	def before_cancel(self):
		je = frappe.db.sql("Select parent from `tabJournal Entry Account` where reference_type = 'MPI Transaction' and reference_name = '{}' limit 1".format(self.name))
		if je:
			doc = frappe.get_doc("Journal Entry",je[0][0])
			if doc.docstatus != 2:
				frappe.throw("Cannot cancel this document as there exists journal entry against this document")

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")

	def post_journal_entry(self):
		bank_account = frappe.db.get_value("Company",self.company,"default_bank_account")
		if not self.net_amount:
			frappe.throw(_("Payable Amount should be greater than zero"))
		sort_cc_wise = defaultdict(list)
		cc_amount = defaultdict(lambda: {'deduction_amount': 0, 'mpi_amount': 0, 'net_mpi_amount':0})

		for a in self.items:
			sort_cc_wise[a.cost_center].append(a)

		for cc, items in sort_cc_wise.items():
			for item in items:
				cc_amount[cc]['deduction_amount'] += flt(item.deduction_amount,2)
				cc_amount[cc]['mpi_amount'] += flt(item.mpi_amount,2)
				cc_amount[cc]['net_mpi_amount'] += flt(item.net_mpi_amount,2)
		je = []
		je.append(self.create_payable_entry(cc_amount))
		je.append(self.be_health_contribution(bank_account))
		je.append(self.be_for_employee(bank_account,cc_amount))
		frappe.msgprint("Following Journal Entry {} Posted against this document".format(frappe.bold(tuple(je))))

	def be_for_employee(self,bank_account,cc_amount):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		accounts = []
		for d in self.items:
			accounts.append({
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
		accounts.append({
			"account": bank_account,
			"credit_in_account_currency": flt(self.net_amount,2),
			"cost_center": self.cost_center
		})
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"title": "MPI Payment to Employee",
			"user_remark": "Note: MPI Payment to Employee",
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.net_amount),
			"branch": self.branch,
			"accounts":accounts
		})
		je.insert()
		return je.name
	def be_health_contribution(self, bank_account):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1
		accounts = []
		accounts.append({
						"account": self.health_contribution_account,
						"debit_in_account_currency": flt(self.total_deduction,2),
						"credit_in_account_currency": 0,            
						"cost_center": self.cost_center,            
						"reference_type": self.doctype,            
						"reference_name": self.name        
					})
		accounts.append({            
						"account": bank_account,            
						"credit_in_account_currency": flt(self.total_deduction,2),            
						"debit_in_account_currency": 0,            
						"cost_center": self.cost_center     
					})
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"title": "Health Contribution from Employee MPI",
			"user_remark": "Note: health contribution from employee mpi",
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.total_deduction),
			"branch": self.branch,
			"accounts":accounts
		})

		je.insert()
		return je.name

	def create_payable_entry(self,cc_amount):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1

		accounts = []
		mpi_expense_account = self.mpi_expense_account
		cost_center = self.cost_center
		payable_account = self.payable_account
		health_contribution_account = self.health_contribution_account
		for d in self.items:
			accounts.append({
				"account": payable_account,
				"credit_in_account_currency": d.net_mpi_amount,
				"cost_center": d.cost_center or cost_center,
				"party_check": 1,
				"party_type": "Employee",
				"party": d.employee,
				"party_name": d.employee_name,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		for key, item in cc_amount.items():
			accounts.append({
				"account": mpi_expense_account,
				"debit_in_account_currency": item.get('mpi_amount'),
				"cost_center": key
			})
		
		accounts.append({
				"account": health_contribution_account,
				"credit_in_account_currency": flt(self.total_deduction),
				"cost_center": self.cost_center,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		total_amount_in_words = money_in_words(self.total_mpi_amount)

		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"title": "MPI Payment to Employee",
			"user_remark": "Note: MPI Payment to Employee",
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": total_amount_in_words,
			"branch": self.branch,
			"accounts": accounts
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
			frappe.throw("Fiscal Year is mandatory")
		if flt(self.mpi_percent) <= 0:
			frappe.throw("MPI percent cannot be 0 or less than 0")

		# fetch basic pay and total days worked for all eligible employees
		sql_query = '''
			SELECT e.name as employee, e.employee_name,
				e.branch, e.cost_center, e.designation,
				e.date_of_joining, 
				(CASE WHEN e.employment_type = 'Contract' 
					THEN e.contract_end_date ELSE e.date_of_retirement END) as relieving_date,
				ss.name as salary_structure,
				sd.amount as basic_pay,
				sd.amount * ssi.working_days as gross_basic_pay,
				ssi.working_days as total_days_worked
			FROM `tabEmployee` e
			INNER JOIN `tabSalary Structure` ss ON ss.eligible_for_mpi = 1 AND ss.employee = e.name AND ss.docstatus = 0
			INNER JOIN `tabSalary Slip` sl ON sl.employee = e.name AND sl.salary_structure = ss.name AND sl.docstatus = 0
			INNER JOIN `tabSalary Detail` sd ON sd.parent = sl.name AND sd.salary_component = 'Basic Pay'
			INNER JOIN `tabSalary Slip Item` ssi ON ssi.parent = sl.name
			WHERE sl.fiscal_year = %(fiscal_year)s
		'''
		params = {'fiscal_year': self.fiscal_year}
		results = frappe.db.sql(sql_query, params, as_dict=True)

		self.set("items", [])
		total_amount = total_mpi_amount = total_deduction = net_amount = 0
		for d in results:
			mpi_amount = flt(flt(d.gross_basic_pay) * flt(self.mpi_percent) / 100, 2)
			deduction_amount = flt(flt(mpi_amount) * flt(self.deduction_percent) / 100, 0)
			net_mpi_amount = flt(flt(mpi_amount) - flt(deduction_amount), 2)
			d.update({
				"mpi_amount": flt(mpi_amount, 2),
				"deduction_amount": flt(deduction_amount, 0),
				"net_mpi_amount": flt(net_mpi_amount, 2)
			})
			total_mpi_amount += flt(mpi_amount, 2)
			total_deduction += flt(deduction_amount, 0)
			total_amount += flt(d.gross_basic_pay, 2)
			net_amount += flt(d.net_mpi_amount, 2)

			self.append("items", d)

		self.total_amount = flt(total_amount, 2)
		self.total_mpi_amount = flt(total_mpi_amount, 2)
		self.total_deduction = flt(total_deduction, 2)
		self.net_amount = flt(net_amount, 2)


			

