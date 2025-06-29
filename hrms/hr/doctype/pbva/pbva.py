# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate ,cint, flt, date_diff, add_months, nowdate
from hrms.hr.hr_custom_functions import get_salary_tax
from frappe.utils import flt, cint, getdate, money_in_words
from collections import defaultdict
from datetime import datetime

class PBVA(Document):
	def validate(self):
		self.calculate_values()
		self.remove_zero_rows()

	def on_submit(self):
		self.post_journal_entry()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")

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
				a.amount	= flt(a.total_basic_pay)*flt(self.pbva_percent)/100
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
		cc_amount = defaultdict(lambda: {"tax_amount":0,"amount":0, "balance_amount":0})

		for a in self.items:
			sort_cc_wise[a.cost_center].append(a)
		
		for cc, items in sort_cc_wise.items():
			for item in items:
				cc_amount[cc]["tax_amount"] += flt(item.tax_amount,2)
				cc_amount[cc]["amount"] += flt(item.amount,2)
				cc_amount[cc]["balance_amount"] += flt(item.balance_amount,2)
		je = []
		je.append(self.create_payable_entry(cc_amount))
		je.append(self.bank_entry_for_employee(cc_amount))
		je.append(self.tax_entry())
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
				"credit": d.balance_amount,
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
				"account": company_doc.pbva_account,
				"debit_in_account_currency": item.get('amount'),
				"debit": item.get('amount'),
				"cost_center": key,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		if flt(self.tax_amount) > 0:
				accounts.append({
					"account": company_doc.salary_tax_account,
					"credit_in_account_currency": flt(self.tax_amount),
					"credit": flt(self.tax_amount),
					"cost_center": self.cost_center,
					"reference_type": self.doctype,
					"reference_name": self.name
				})
		total_amount_in_words = money_in_words(self.net_amount)

		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"title": "{}% PBVA to Employee".format(self.pbva_percent),
			"user_remark": "Note: {}% PBVA Payment to Employee".format(self.pbva_percent),
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": total_amount_in_words,
			"branch": self.branch,
			"accounts": accounts
		})

		je.insert()
		je.submit()
		return je.name

	def bank_entry_for_employee(self,cc_amount):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		accounts = []
		company_doc = frappe.get_doc("Company", self.company)
		for d in self.items:
			accounts.append({
				"account": company_doc.employee_payable_account,
				"debit_in_account_currency": flt(d.balance_amount,2),
				"debit": flt(d.balance_amount,2),
				"cost_center": d.cost_center or self.cost_center,
				"party_check": 1,
				"party_type": "Employee",
				"party": d.employee,
				"party_name": d.employee_name,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		accounts.append({
			"account": company_doc.default_bank_account,
			"credit_in_account_currency": flt(self.net_amount,2),
			"credit": flt(self.net_amount,2),
			"cost_center": self.cost_center,
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

	def tax_entry(self):
		if flt(self.tax_amount) > 0:
			je = frappe.new_doc("Journal Entry")
			je.flags.ignore_permissions=1
			accounts = []
			company_doc = frappe.get_doc("Company", self.company)
			accounts.append({
				"account": company_doc.default_bank_account,
				"credit_in_account_currency": flt(self.tax_amount,2),
				"credit": flt(self.tax_amount,2),
				"cost_center": self.cost_center,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
			if flt(self.tax_amount) > 0:
				accounts.append({
					"account": company_doc.salary_tax_account,
					"debit_in_account_currency": flt(self.tax_amount,2),
					"debit": flt(self.tax_amount,2),
					"cost_center": self.cost_center,
					"reference_type": self.doctype,
					"reference_name": self.name
				})
			je.update({
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"title": "Tax Entry for {}% PBVA".format(self.pbva_percent),
				"user_remark": "Note: Tax Entry for {}% PBVA Payment to Employee tax entry".format(self.pbva_percent),
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
			frappe.throw("PBVA percent cannot be 0 or less than 0")
		#start, end = frappe.db.get_value("Fiscal Year", self.fiscal_year, ["year_start_date", "year_end_date"])
		start = str(self.fiscal_year)+'-01-01'
		end   = str(self.fiscal_year)+'-12-31'
		days_in_year = date_diff(end, start)+1
		query = """select
					e.name as employee,
					e.employee_name,
					e.status,
					e.passport_number,
					e.employment_type,
					e.tpn_number,
					e.branch,
					e.date_of_joining,
					e.relieving_date,
					e.salary_mode,
					e.department,
					e.bank_name,
					e.bank_ac_no,
					e.bank_branch,
					e.pbva_percent,
					(select fib.financial_system_code from `tabFinancial Institution Branch` fib where fib.name = e.bank_branch) financial_system_code,
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
												and sl.docstatus = 1
												and sl.fiscal_year = {0}
						and (sd.salary_component = 'Basic Pay'
														or exists(select 1 from `tabSalary Component` sc
																		where sc.name = sd.salary_component
																		and sc.is_pf_deductible = 1
																		and sc.type = 'Earning')
												)
												and exists(select 1
																from `tabSalary Slip Item` ssi, `tabSalary Structure` ss
																where ssi.parent = sl.name
																and ss.name = ssi.salary_structure
																and ss.eligible_for_pbva = 1)
												order by sl.month desc limit 1
										) as basic_pay,
										(
												select
														sum(sd.amount)
												from
														`tabSalary Detail` sd,
														`tabSalary Slip` sl
												where sd.parent = sl.name
												and sl.employee = e.name
												and sd.salary_component = 'Basic Pay'
												and sl.docstatus = 1
												and sl.fiscal_year = {0}
						and (sd.salary_component = 'Basic Pay'
														or exists(select 1 from `tabSalary Component` sc
																		where sc.name = sd.salary_component
																		and sc.is_pf_deductible = 1
																		and sc.type = 'Earning')
												)
												and exists(select 1
																from `tabSalary Slip Item` ssi, `tabSalary Structure` ss
																where ssi.parent = sl.name
																and ss.name = ssi.salary_structure
																and ss.eligible_for_pbva = 1)
										)+ifnull((select sum(ebd.amount) from `tabSeparation Item` ebd, `tabEmployee Benefit Type` bt, `tabEmployee Benefits` eb where ebd.parent = eb.name
										and eb.docstatus = 1 and year(eb.separation_date) = '{0}'
										and ebd.benefit_type = bt.name
										and bt.include_in_pbva = 1
										and eb.employee = e.name),0)+ifnull((select sum(sapi.arrear_basic_pay) from `tabSalary Arrear Payment Item` sapi, `tabSalary Arrear Payment` sap where sapi.parent = sap.name
										and sap.docstatus = 1 and sap.fiscal_year = '{0}'
										and sapi.employee = e.name),0) as total_basic_pay,
										case when e.pbva_percent > 0 then
										(((
												select
														sum(sd.amount)
												from
														`tabSalary Detail` sd,
														`tabSalary Slip` sl
												where sd.parent = sl.name
												and sl.employee = e.name
												and sd.salary_component = 'Basic Pay'
												and sl.docstatus = 1
												and sl.fiscal_year = {0}
						and (sd.salary_component = 'Basic Pay'
														or exists(select 1 from `tabSalary Component` sc
																		where sc.name = sd.salary_component
																		and sc.is_pf_deductible = 1
																		and sc.type = 'Earning')
												)
												and exists(select 1
																from `tabSalary Slip Item` ssi, `tabSalary Structure` ss
																where ssi.parent = sl.name
																and ss.name = ssi.salary_structure
																and ss.eligible_for_pbva = 1)
										)+(select ifnull(sum(ebd.amount),0) from `tabSeparation Item` ebd, `tabEmployee Benefit Type` bt, `tabEmployee Benefits` eb where ebd.parent = eb.name
										and eb.docstatus = 1 and year(eb.separation_date) = '{0}'
										and ebd.benefit_type = bt.name
										and bt.include_in_pbva = 1
										and eb.employee = e.name))/100*e.pbva_percent)
										else
				(((
												select
														sum(sd.amount)
												from
														`tabSalary Detail` sd,
														`tabSalary Slip` sl
												where sd.parent = sl.name
												and sl.employee = e.name
												and sd.salary_component = 'Basic Pay'
												and sl.docstatus = 1
												and sl.fiscal_year = {0}
						and (sd.salary_component = 'Basic Pay'
														or exists(select 1 from `tabSalary Component` sc
																		where sc.name = sd.salary_component
																		and sc.is_pf_deductible = 1
																		and sc.type = 'Earning')
												)
												and exists(select 1
																from `tabSalary Slip Item` ssi, `tabSalary Structure` ss
																where ssi.parent = sl.name
																and ss.name = ssi.salary_structure
																and ss.eligible_for_pbva = 1)
										)+(select ifnull(sum(ebd.amount),0) from `tabSeparation Item` ebd, `tabEmployee Benefit Type` bt, `tabEmployee Benefits` eb where ebd.parent = eb.name
										and eb.docstatus = 1 and year(eb.separation_date) = '{0}'
										and ebd.benefit_type = bt.name
										and bt.include_in_pbva = 1
										and eb.employee = e.name))/100*{5})
										end as amount
								from tabEmployee e
								where (
										('{3}' = 'Active' and e.date_of_joining <= '{2}' and ifnull(e.relieving_date,'9999-12-31') > '{2}')
										or
										('{3}' = 'Left' and ifnull(e.relieving_date,'9999-12-31') <= '{6}')
										or
										('{3}' = 'All' and e.date_of_joining <= '{2}' and ifnull(e.relieving_date,'9999-12-31') >= '{1}')
										)
								and 
								case when '{3}' = 'Active' then (select ss.eligible_for_pbva from `tabSalary Structure` ss where ss.employee = e.name and ss.is_active = 'Yes') = 1 and e.status = 'Active'
								when '{3}' = 'Left' then (select ss.eligible_for_pbva from `tabSalary Structure` ss where ss.employee = e.name and e.employment_status = 'Left' and month(e.relieving_date) > 3 and ss.docstatus < 2 order by ss.creation desc limit 1) = 1
								when '{3}' = 'All' then (select ss.eligible_for_pbva from `tabSalary Structure` ss where ss.employee = e.name and ss.docstatus < 2 order by ss.creation desc limit 1) = 1 end
								and not exists(
												select 1
												from `tabPBVA Details` bd, `tabPBVA` b
												where b.fiscal_year = '{0}'
												and b.name != '{4}'
												and bd.parent = b.name
												and bd.employee = e.employee
												and b.docstatus in (0,1))
								order by e.branch
						""".format(self.fiscal_year, start, end, self.employee_status, self.name, self.pbva_percent, nowdate())
		# frappe.msgprint(query)
		entries = frappe.db.sql(query, as_dict=True)
		self.set('items', [])

		start = getdate(start)
		end = getdate(end)

		for d in entries:
			# d.amount = 0
			row = self.append('items', {})
			total_leave_days = 0
		# 	d.dep_rating = frappe.db.get_value(
       	# 			"Performance Evaluation",
        #    			{
        #           		"employee": frappe.db.get_value("Department", d.department, "approver"),
		# 				"pms_calendar": self.fiscal_year
        #             },
		# 			"final_score_percent"
        #    )
			# 	d.employee_rating =frappe.db.get_value(
			# 			"Performance Evaluation",
			#    			{
			#           		"employee": d.employee,
			# 				"pms_calendar": self.fiscal_year
			#             },
			# 			"final_score_percent"
			#    )
			employee_rating =frappe.db.sql("""
                                    select count(name) as nos, sum(final_score_percent) as final_score
                                    from `tabPerformance Evaluation` where docstatus = 1 and employee = '{}'
                                    and pms_calendar = '{}'
                                    """.format(d.employee, self.fiscal_year), as_dict = 1)
			if frappe.db.get_value("Employee", d.employee, "pbva_percent") == 0 or not frappe.db.get_value("Employee", d.employee, "pbva_percent"):
				if not d.dep_rating or d.dep_rating == 0:
					d.dep_rating = flt(frappe.db.get_value("Department", frappe.db.get_value("Employee", d.employee, "department"), "unit_rating"))
				d.dep_rating = 0 if not d.dep_rating else d.dep_rating * 0.5
				d.employee_rating = 0
				if employee_rating:
					d.employee_rating = employee_rating[0].final_score
				if not d.employee_rating:
					d.employee_rating = 0
				d.employee_rating = d.employee_rating * 0.5
				d.total_rating = d.dep_rating+d.employee_rating
				# if frappe.db.get_single_value("HR Settings", "use_flat_pbva") == 0:
				if self.company_achievement < 95:
					if d.total_rating < self.company_achievement:
						d.pbva_percent = flt((d.total_rating/self.company_achievement)*(self.pbva_percent),3)
					else:
						d.pbva_percent = self.pbva_percent
				else:
					if d.total_rating < 95:
						d.pbva_percent = flt((d.total_rating/95)*(self.pbva_percent),3)
					else:
						d.pbva_percent = self.pbva_percent
				# else:
				# 	d.pbva_percent = flt(self.pbva_percent, 3)
			else:
				d.pbva_percent = flt(frappe.db.get_value("Employee", d.employee, "pbva_percent"),3)

			d.total_basic_pay = 0 if not d.total_basic_pay else d.total_basic_pay
			days_in_year = date_diff(end, start)+1
			total_leave_days = frappe.db.sql("select sum(ifnull(total_leave_days,0)) as leaves from `tabLeave Application` where docstatus = 1 and employee = '{}' and year(from_date) = '{}' and leave_type not in ('Maternity Leave', 'Study Leave', 'EOL')".format(d.employee, self.fiscal_year), as_dict=1)

			if len(total_leave_days) > 0:
				total_leave_days = total_leave_days[0].leaves
			else:
				total_leave_days = 0
			if not total_leave_days:
				total_leave_days = 0
			if flt(total_leave_days) > 30:
				total_leave_days -= 30
			else:
				total_leave_days = 0
			if str(d.date_of_joining).split("-")[0] == str(self.fiscal_year) and flt(str(d.date_of_joining).split("-")[1]) < 7:
				d.days_worked = date_diff(datetime.strptime(str(self.fiscal_year)+"-12-31", "%Y-%m-%d").date(), datetime.strptime(str(self.fiscal_year)+"-"+str(int(str(d.date_of_joining).split("-")[1])+6)+"-"+str(d.date_of_joining).split("-")[2], "%Y-%m-%d").date())+1
				days_in_year = flt(date_diff(datetime.strptime(str(self.fiscal_year)+"-12-31", "%Y-%m-%d").date(), datetime.strptime(str(d.date_of_joining), "%Y-%m-%d").date()))
				# d.no_probation = 0
			elif str(d.date_of_joining).split("-")[0] == str(self.fiscal_year) and flt(str(d.date_of_joining).split("-")[1]) >= 7:
				d.days_worked = 0
				# d.no_probation = 0
			if str(d.date_of_joining).split("-")[0] == str(int(self.fiscal_year)-1) and flt(str(d.date_of_joining).split("-")[1]) > 6:
				d.days_worked = date_diff(datetime.strptime(str(self.fiscal_year)+"-12-31", "%Y-%m-%d").date(), datetime.strptime(str(add_months(d.date_of_joining,6)), "%Y-%m-%d").date())+1
				days_in_year = flt(date_diff(datetime.strptime(str(self.fiscal_year)+"-12-31", "%Y-%m-%d").date(), datetime.strptime(str(self.fiscal_year)+"-01-01", "%Y-%m-%d").date()))+1
				# if d.no_probation != 1:
				# 	d.no_probation = 0
			# if str(d.date_of_joining).split("-")[0] != str(int(self.fiscal_year)-1) and str(d.date_of_joining).split("-")[0] != str(self.fiscal_year):
			# 	d.no_probation = 1

			d.days_worked = d.days_worked - total_leave_days
			if d.days_worked < 0:
				d.days_worked = 0
			# if d.status == 'Active':
				# if d.no_probation == 0:
				# else:
				# 	d.amount = flt(flt(flt(d.pbva_percent/100)*d.total_basic_pay),2)
			d.amount = flt((flt(flt(d.pbva_percent/100)*d.total_basic_pay)/days_in_year)*d.days_worked,2)
			# else:
			# 	d.amount = flt(flt(flt(d.pbva_percent/100)*d.total_basic_pay),2)
			row.update(d)
			'''
			joining = getdate(d.date_of_joining)
			relieving = getdate(d.relieving_date)

			if not (joining >= start and joining <= end): 
				d.date_of_joining = None
			if not (relieving >= start and relieving <= end): 
				d.relieving_date = None

			d.days_worked = date_diff(getdate(self.fiscal_year + '-12-31'), getdate(self.fiscal_year + '-01-01'))
			if d.date_of_joining: 
				d.days_worked = date_diff(getdate(self.fiscal_year + '-12-31'), d.date_of_joining)

			if d.relieving_date:
				d.days_worked = date_diff(d.relieving_date, getdate(self.fiscal_year + '-01-01'))
	
			if d.relieving_date and d.date_of_joining:
								d.days_worked = date_diff(d.relieving_date, d.date_of_joining)

			d.days_worked = cint(d.days_worked) + 1
			'''
		#deductions
		# for ded in self.deductions:
		# 	for emp in self.items:
		# 		if ded.employee == emp.employee:
		# 			if emp.amount - ded.amount < 0:
		# 				frappe.throw("PBVA amount for Employee {} is less than 0".format(emp.employee))
			