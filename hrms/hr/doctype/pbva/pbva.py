# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate ,cint, flt
from hrms.hr.hr_custom_functions import get_salary_tax
from frappe.utils import flt, cint, getdate, money_in_words
from collections import defaultdict

class PBVA(Document):
	def validate(self):
		self.calculate_values()
		self.remove_zero_rows()

	def on_submit(self):
		self.post_journal_entry()
	def before_cancel(self):
		je = frappe.db.sql("Select parent from `tabJournal Entry Account` where reference_type = 'PBVA' and reference_name = '{}' limit 1".format(self.name))
		if je:
			doc = frappe.get_doc("Journal Entry",je[0][0])
			if doc.docstatus != 2:
				frappe.throw("Cannot cancel this document as there exists journal entry against this document")

	def calculate_values(self):
		if self.items:
			tot = tax = net = 0
			for a in self.items:
				a.tax_amount = flt(get_salary_tax(a.amount),2)
				a.balance_amount = flt(flt(a.amount,2) - flt(a.tax_amount,2),2)
				tot += flt(a.amount,2)
				tax += flt(a.tax_amount,2)
				net += flt(a.balance_amount,2)

			self.total_amount = tot
			self.tax_amount   = tax
			self.net_amount   = net
		else:
			frappe.throw("Cannot save without employee details")

	def remove_zero_rows(self):
		if self.items:
			to_remove = []
			for d in self.items:
				if d.amount == 0:
					to_remove.append(d)
			[self.remove(d) for d in to_remove]
	
	def post_journal_entry(self):
		if not self.net_amount:
			frappe.throw(_("Payable Amount should be greater than zero"))
		sort_cc_wise = defaultdict(list)
		cc_amount = defaultdict(lambda: {"tax_amount":0,"net_amount":0, "balance_amount":0})

		for a in self.items:
			sort_cc_wise[a.cost_center].append(a)
		
		for cc, items in sort_cc_wise.items():
			for item in items:
				cc_amount[cc]["tax_amount"] += flt(item.tax_amount,2)
				cc_amount[cc]["net_amount"] += flt(item.amount,2)
				cc_amount[cc]["balance_amount"] += flt(item.balance_amount,2)
		je = []
		je.append(self.create_payable_entry(cc_amount))
		je.append(self.bank_entry_for_employee(cc_amount))
		je.append(self.tax_entry(cc_amount))
		frappe.msgprint("Following Journal Entry {} Posted against this document".format(frappe.bold(tuple(je))))

	def create_payable_entry(self, cc_amount):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1

		accounts = []
		cost_center = self.cost_center
		company_doc = frappe.get_doc("Company", self.company)
		for d in self.items:
			accounts.append({
				"account": company_doc.employee_payable_account,
				"credit_in_account_currency": d.balance_amount,
				"cost_center": d.cost_center or cost_center,
				"party_check": 1,
				"party_type": "Employee",
				"party": d.employee,
				"party_name": d.employee_name,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		for key, item in cc_amount.items():
			if item.get('tax_amount') > 0:
				accounts.append({
					"account": company_doc.salary_tax_account,
					"credit_in_account_currency": item.get('tax_amount'),
					"cost_center": key,
					"reference_type": self.doctype,
					"reference_name": self.name
				})

			accounts.append({
				"account": company_doc.pbva_account,
				"debit_in_account_currency": item.get('net_amount'),
				"cost_center": key,
				"reference_type": self.doctype,
				"reference_name": self.name
			})

		total_amount_in_words = money_in_words(self.net_amount)

		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"title": "{}% Pbva to Employee".format(self.pbva_percent),
			"user_remark": "Note: {}% Pbva Payment to Employee".format(self.pbva_percent),
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": total_amount_in_words,
			"branch": self.branch,
			"accounts": accounts
		})

		je.insert()
		return je.name

	def bank_entry_for_employee(self,cc_amount):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		accounts = []
		company_doc = frappe.get_doc("Company", self.company)
		club_cc_wise = {}
		for d in self.items:
			accounts.append({
				"account": company_doc.employee_payable_account,
				"debit_in_account_currency": flt(d.balance_amount,2),
				"cost_center": d.cost_center or self.cost_center,
				"party_check": 1,
				"party_type": "Employee",
				"party": d.employee,
				"party_name": d.employee_name,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		for key, item in cc_amount.items():
			accounts.append({
				"account": company_doc.default_bank_account,
				"credit_in_account_currency": flt(item.get('balance_amount'),2),
				"cost_center": key,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"title": "{}% PBVA Payment to Employee".format(self.pbva_percent),
			"user_remark": "Note: {}% PBVA Payment to Employee".format(self.pbva_percent),
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.net_amount),
			"branch": self.branch,
			"accounts":accounts
		})
		je.insert()
		return je.name

	def tax_entry(self,cc_amount):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		accounts = []
		company_doc = frappe.get_doc("Company", self.company)
		club_cc_wise = {}
		for key, item in cc_amount.items():
			if flt(item.get('tax_amount'),2) > 0:
				accounts.append({
					"account": company_doc.default_bank_account,
					"credit_in_account_currency": flt(item.get('tax_amount'),2),
					"cost_center": key,
					"reference_type": self.doctype,
					"reference_name": self.name
				})
				if item.get('tax_amount') > 0:
					accounts.append({
						"account": company_doc.salary_tax_account,
						"debit_in_account_currency": item.get('tax_amount'),
						"cost_center": key,
						"reference_type": self.doctype,
						"reference_name": self.name
					})
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"title": "{}% PBVA Payment to Employee tax entry".format(self.pbva_percent),
			"user_remark": "Note: {}% PBVA Payment to Employee tax entry".format(self.pbva_percent),
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.net_amount),
			"branch": self.branch,
			"accounts":accounts
		})
		je.insert()
		return je.name

	@frappe.whitelist()
	def get_pbva_details(self):
		if not self.fiscal_year:
			frappe.throw("Fiscal Year is Mandatory")
		if not self.pbva_percent:
			frappe.throw("PBVA percent is Mandatory")
		if self.pbva_percent <= 0 :
			frappe.throw("PBVA percent cannot be 0 or less than 0")
		start = str(self.fiscal_year)+'-01-01'
		end   = str(self.fiscal_year)+'-12-31'
		# query = """select
		# 		e.name as employee,
		# 		e.employee_name,
		# 		e.employment_type,
		# 		e.branch,
		# 		e.date_of_joining,
		# 		e.relieving_date,
		# 		# e.reason_for_resignation as leaving_type,
		# 		e.salary_mode,
		# 		e.bank_name,
		# 		e.bank_ac_no,
		# 		e.cost_center,
		# 		datediff(least(ifnull(e.relieving_date,'9999-12-31'),'{2}'),
		# 		greatest(e.date_of_joining,'{1}'))+1 days_worked,
		# 		(select
		# 			sd.amount
		# 			from
		# 				`tabSalary Detail` sd,
		# 				`tabSalary Slip` sl
		# 			where sd.parent = sl.name
		# 			and sl.employee = e.name
		# 			and sd.salary_component = 'Basic Pay'
		# 			and sl.docstatus = 1
		# 			and sl.fiscal_year = {0}
		# 			and (sd.salary_component = 'Basic Pay'
		# 			or exists(select 1 from `tabSalary Component` sc
		# 				where sc.name = sd.salary_component
		# 				and sc.is_pf_deductible = 1
		# 				and sc.type = 'Earning')
		# 				)
		# 				and exists(select 1
		# 					from `tabSalary Slip Item` ssi, `tabSalary Structure` ss
		# 					where ssi.parent = sl.name
		# 					and ss.name = ssi.salary_structure
		# 					and ss.eligible_for_pbva = 1)
		# 				order by sl.month desc limit 1
		# 		) as basic_pay,
		# 		(select
		# 			sum(sd.amount)
		# 			from
		# 				`tabSalary Detail` sd,
		# 				`tabSalary Slip` sl
		# 			where sd.parent = sl.name
		# 			and sl.employee = e.name
		# 			and sd.salary_component = 'Basic Pay'
		# 			and sl.docstatus = 1
		# 			and sl.fiscal_year = {0}
		# 			and (sd.salary_component = 'Basic Pay'
		# 			or exists(select 1 from `tabSalary Component` sc
		# 				where sc.name = sd.salary_component
		# 				and sc.is_pf_deductible = 1
		# 				and sc.type = 'Earning')
		# 		)
		# 		and exists(select 1
		# 			from 
		# 				`tabSalary Slip Item` ssi,
		# 				 `tabSalary Structure` ss
		# 			where ssi.parent = sl.name
		# 			and ss.name = ssi.salary_structure
		# 			and ss.eligible_for_pbva = 1)
		# 		) as total_basic_pay,
		# 		((select
		# 			sum(sd.amount)
		# 			from
		# 				`tabSalary Detail` sd,
		# 				`tabSalary Slip` sl
		# 			where sd.parent = sl.name
		# 			and sl.employee = e.name
		# 			and sd.salary_component = 'Basic Pay'
		# 			and sl.docstatus = 1
		# 			and sl.fiscal_year = {0}
		# 			and (sd.salary_component = 'Basic Pay'
		# 		or exists(select 1 from `tabSalary Component` sc
		# 			where sc.name = sd.salary_component
		# 			and sc.is_pf_deductible = 1
		# 			and sc.type = 'Earning')
		# 		)
		# 		and exists(select 1
		# 			from 
		# 				`tabSalary Slip Item` ssi, 
		# 				`tabSalary Structure` ss
		# 			where ssi.parent = sl.name
		# 			and ss.name = ssi.salary_structure
		# 			and ss.eligible_for_pbva = 1)
		# 		)/100*{5}) as amount
		# 		from tabEmployee e
		# 		where (
		# 				('{3}' = 'Active' and e.date_of_joining <= '{2}' and ifnull(e.relieving_date,'9999-12-31') > '{2}')
		# 				or
		# 				('{3}' = 'Left' and ifnull(e.relieving_date,'9999-12-31') between '{1}' and '{2}')
		# 				or
		# 				('{3}' = 'All' and e.date_of_joining <= '{2}' and ifnull(e.relieving_date,'9999-12-31') >= '{1}')
		# 			)
		# 		and not exists(select 1
		# 			from 
		# 				`tabPBVA Details` bd,
		# 				 `tabPBVA` b
		# 			where b.fiscal_year = '{0}'
		# 			and b.name <> '{4}'
		# 			and bd.parent = b.name
		# 			and bd.employee = e.employee
		# 			and b.docstatus in (0,1))
		# 		order by e.branch
		# 				""".format(self.fiscal_year, start, end, self.employee_status, self.name, self.pbva_percent)
		query = """SELECT
						e.name as employee,
						e.employee_name,
						e.employment_type,
						e.branch,
						e.date_of_joining,
						e.relieving_date,
						e.salary_mode,
						e.bank_name,
						e.bank_ac_no,
						e.cost_center,
						datediff(least(ifnull(e.relieving_date, '9999-12-31'), '{2}'), greatest(e.date_of_joining, '{1}')) + 1 AS days_worked,
						sd.amount AS basic_pay,
						SUM(sd.amount) AS total_basic_pay,
						(SUM(sd.amount)/100*{5}) AS amount
					FROM
						tabEmployee e
						LEFT JOIN `tabSalary Slip` sl ON sl.employee = e.name AND sl.docstatus = 1 AND sl.fiscal_year = {0}
						LEFT JOIN `tabSalary Detail` sd ON sd.parent = sl.name AND sd.salary_component = 'Basic Pay'
					WHERE
						(
							('{3}' = 'Active' AND e.date_of_joining <= '{2}' AND IFNULL(e.relieving_date, '9999-12-31') > '{2}')
							OR
							('{3}' = 'Left' AND IFNULL(e.relieving_date, '9999-12-31') BETWEEN '{1}' AND '{2}')
							OR
							('{3}' = 'All' AND e.date_of_joining <= '{2}' AND IFNULL(e.relieving_date, '9999-12-31') >= '{1}')
						)
						AND NOT EXISTS (
							SELECT 1
							FROM `tabPBVA Details` bd
							INNER JOIN `tabPBVA` b ON b.name <> '{4}' AND bd.parent = b.name AND bd.employee = e.employee AND b.docstatus IN (0,1)
							WHERE b.fiscal_year = '{0}'
						)
					GROUP BY
						e.name,
						e.employee_name,
						e.employment_type,
						e.branch,
						e.date_of_joining,
						e.relieving_date,
						e.salary_mode,
						e.bank_name,
						e.bank_ac_no,
						e.cost_center,
						days_worked,
						basic_pay
					ORDER BY
						e.branch;
		""".format(self.fiscal_year, start, end, self.employee_status, self.name, self.pbva_percent)
		
		entries = frappe.db.sql(query, as_dict=True)
		self.set('items', [])

		start = getdate(start)
		end = getdate(end)
		for d in entries:
			# d.amount = 0
			row = self.append('items', {})
			row.update(d)
			