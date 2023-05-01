# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, cint, date_diff, today, money_in_words
from hrms.hr.hr_custom_functions import get_salary_tax
from collections import defaultdict

class Bonus(Document):
	def validate(self):
		self.calculate_values()
		self.validate_bonus_amount()
		self.validate_duplicate()
	
	def before_cancel(self):
		je = frappe.db.sql("Select parent from `tabJournal Entry Account` where reference_type = '{}' and reference_name = '{}' limit 1".format(self.doctype,self.name))
		if je:
			doc = frappe.get_doc("Journal Entry",je[0][0])
			if doc.docstatus != 2:
				frappe.throw("Cannot cancel this document as there exists journal entry against this document")
	
	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")
	
	def on_submit(self):
		self.post_journal_entry()

	def post_journal_entry(self):
		company_doc = frappe.get_doc("Company",self.company)
		bank_account = company_doc.default_bank_account
		tax_account = company_doc.salary_tax_account
		bonus_account = company_doc.bonus_account
		payable_account = company_doc.employee_payable_account
		if not self.net_amount:
			frappe.throw(_("Payable Amount should be greater than zero"))
		sort_cc_wise = defaultdict(list)
		cc_amount = defaultdict(lambda: {'amount': 0, 'tax': 0, 'balance_amount':0})

		for a in self.items:
			sort_cc_wise[a.cost_center].append(a)

		for cc, items in sort_cc_wise.items():
			for item in items:
				cc_amount[cc]['amount'] += flt(item.amount,2)
				cc_amount[cc]['tax'] += flt(item.tax_amount,2)
				cc_amount[cc]['balance_amount'] += flt(item.balance_amount,2)
		je = []
		je.append(self.create_payable_entry(cc_amount, tax_account, bonus_account , payable_account))
		je.append(self.tax_entry( bank_account, tax_account))
		je.append(self.be_for_employee(bank_account, payable_account, cc_amount))
		frappe.msgprint("Following Journal Entry {} Posted against this document".format(frappe.bold(tuple(je))))
	
	def be_for_employee(self, bank_account, payable_account, cc_amount):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		accounts = []
		for d in self.items:
			accounts.append({
				"account": payable_account,
				"debit_in_account_currency": flt(d.balance_amount,2),
				"cost_center": d.cost_center or self.cost_center,
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
			"title": "Annual Bonus Payment to Employee",
			"user_remark": "Note: Annual Bonus Payment to Employee",
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.net_amount),
			"branch": self.branch,
			"accounts":accounts
		})
		je.insert()
		return je.name
	def tax_entry(self, bank_account,tax_account):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1
		accounts = []
		accounts.append({
						"account": tax_account,
						"debit_in_account_currency": flt(self.tax_amount,2),
						"credit_in_account_currency": 0,            
						"cost_center": self.cost_center,            
						"reference_type": self.doctype,            
						"reference_name": self.name        
					})
		accounts.append({            
						"account": bank_account,            
						"credit_in_account_currency": flt(self.tax_amount,2),            
						"debit_in_account_currency": 0,            
						"cost_center": self.cost_center     
					})
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"title": "Tax Deduction from Employee Bonus",
			"user_remark": "Note: Tax Deduction from Employee Bonus",
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.tax_amount),
			"branch": self.branch,
			"accounts":accounts
		})

		je.insert()
		return je.name

	def create_payable_entry(self,cc_amount, tax_account, bonus_account, payable_account):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1

		accounts = []
		for d in self.items:
			accounts.append({
				"account": payable_account,
				"credit_in_account_currency": d.balance_amount,
				"cost_center": d.cost_center,
				"party_check": 1,
				"party_type": "Employee",
				"party": d.employee,
				"party_name": d.employee_name,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		for key, item in cc_amount.items():
			accounts.append({
				"account": bonus_account,
				"debit_in_account_currency": item.get('amount'),
				"cost_center": key
			})
		
		accounts.append({
				"account": tax_account,
				"credit_in_account_currency": flt(self.tax_amount),
				"cost_center": self.cost_center,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		total_amount_in_words = money_in_words(self.total_amount)

		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"title": "Annual Bonus Payment to Employee",
			"user_remark": "Note: Annual Bonus Payment to Employee",
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": total_amount_in_words,
			"branch": self.branch,
			"accounts": accounts
		})

		je.insert()
		return je.name

	def validate_duplicate(self):
		doc = frappe.db.sql("select name from `tabBonus` where docstatus != 1 and fiscal_year = \'"+str(self.fiscal_year)+"\' and name != \'"+str(self.name)+"\'")	
		if doc:
			frappe.throw("Can not create multiple Bonuses for the same year")

	def validate_bonus_amount(self):
		if self.items:
			count = 1
			for a in self.get("items"):
				if not a.amount or a.amount == 0:
					frappe.throw("Bonus amount for Employee {} ({}) at row {} cannot be 0".format(a.employee, a.employee_name, count))
				count += 1
				
	def calculate_values(self):
		if self.items:
			amounts = {"total": 0, "tax": 0, "net": 0}
			for a in self.items:
				# total_bonus_amount = flt(flt(a.basic_pay) * flt(self.bonus_slab),2)
				# bonus_per_day = flt(flt(total_bonus_amount) / 365,2)
				# a.amount = flt(bonus_per_day * a.days_worked,2)
				a.tax_amount = flt(get_salary_tax(a.amount),2)
				a.balance_amount = flt(flt(a.amount) - flt(a.tax_amount),2)
				amounts["total"] += flt(a.amount,2)
				amounts["tax"] += flt(a.tax_amount,2)
				amounts["net"] += flt(a.balance_amount,2)
			self.total_amount = flt(amounts["total"],2)
			self.tax_amount = flt(amounts["tax"],2)
			self.net_amount = flt(amounts["net"],2)
		else:
			frappe.throw("Cannot save without employee details")

	#Populate Bonus details 
	@frappe.whitelist()
	def get_employees(self):
		if not self.fiscal_year:
			frappe.throw("Fiscal Year is Mandatory")
		#start, end = frappe.db.get_value("Fiscal Year", self.fiscal_year, ["year_start_date", "year_end_date"])
		start = str(self.fiscal_year)+'-01-01'
		end   = str(self.fiscal_year)+'-12-31'
		
		entries = frappe.db.sql("""
				select
					e.name as employee,
					e.employee_name,
					e.employment_type,
					e.branch,
					e.cost_center,
					e.date_of_joining,
					e.relieving_date,
					e.salary_mode,
					e.bank_name,
					e.bank_ac_no,
					datediff(least(ifnull(e.relieving_date,'9999-12-31'),'{2}'),
					greatest(e.date_of_joining,'{1}'))+1 days_worked,
					(
						select
							sd.amount
						from
							`tabSalary Detail` sd,
							`tabSalary Slip` sl
						where sd.parent = sl.name
						and sl.employee = e.name
						and sd.salary_component = 'Basic Pay'
						and sl.actual_basic = 0
						and sl.docstatus = 1
						and sl.fiscal_year = '{0}'
						and exists(select 1
							from 
								`tabSalary Slip Item` ssi, 
								`tabSalary Structure` ss
							where ssi.parent = sl.name
							and ss.name = ssi.salary_structure
							and ss.eligible_for_annual_bonus = 1)
						order by sl.month desc limit 1
					) as basic_pay
				from tabEmployee e
				where (
						('{3}' = 'Active' and e.date_of_joining <= '{2}' and ifnull(e.relieving_date,'9999-12-31') > '{2}')
						or
						('{3}' = 'Left' and ifnull(e.relieving_date,'9999-12-31') between '{1}' and '{2}')
						or
						('{3}' = 'All' and e.date_of_joining <= '{2}' and ifnull(e.relieving_date,'9999-12-31') >= '{1}')
						)
				and not exists(
					select 1
					from 
						`tabBonus Details` bd,
						`tabBonus` b
					where b.fiscal_year = '{0}'
					and b.name <> '{4}'
					and bd.parent = b.name
					and bd.employee = e.employee
					and b.docstatus in (0,1))
				order by e.branch
				""".format(self.fiscal_year, start, end, self.employee_status, self.name), as_dict=True)
		self.set('items', [])
		start = getdate(start)
		end = getdate(end)

		for d in entries:
				d.amount = 0
				row = self.append('items', {})
				row.update(d)
	def on_cancel(self):
		jv = frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus")
		if jv != 2:
			frappe.throw("Can not cancel Bonus Entry without canceling the corresponding journal entry " + str(self.journal_entry))
		else:
			self.db_set("journal_entry", "")



