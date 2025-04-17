# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate ,cint, flt
from hrms.hr.hr_custom_functions import get_salary_tax
from frappe.utils import flt, cint, getdate, money_in_words, date_diff, add_months, add_days
from collections import defaultdict
from datetime import datetime

class PBVI(Document):
	def validate(self):
		self.calculate_values()
		self.remove_zero_rows()

	def validate_amount(self):
		for d in self.items:
			if flt(d.deduction_amount) < 0:
				frappe.throw(_("Row#{}: <b>Deductions</b> cannot be less than zero").format(d.idx))
			elif flt(d.balance_amount) < 0:
				frappe.throw(_("Row#{}: <b>PBVI After Tax</b> cannot be less than zero").format(d.idx))

	def on_submit(self):
		self.validate_amount()
		# cc_amount = {}
		# for a in self.items:
		# 	# tax = get_salary_tax(a.amount)
		# 	cost_center, ba = frappe.db.get_value("Employee", a.employee, ["cost_center", "business_activity"])
		# 	cc = str(str(cost_center) + ":" + str(ba))
		# 	if cc in cc_amount:
		# 		cc_amount[cc]['amount'] = flt(cc_amount[cc]['amount'],2) + flt(a.amount,2)
		# 		cc_amount[cc]['tax'] = flt(cc_amount[cc]['tax'],2) + flt(a.tax_amount,2)
		# 		cc_amount[cc]['deduction'] = flt(cc_amount[cc]['deduction'],2) + flt(a.deduction_amount,2)
		# 		cc_amount[cc]['balance_amount'] = flt(cc_amount[cc]['balance_amount'],2) + flt(a.balance_amount,2)
		# 	else:
		# 		row = {"amount": flt(a.amount,2), "tax": flt(a.tax_amount,2), \
		# 			"deduction": flt(a.deduction_amount,2), "balance_amount": flt(a.balance_amount,2)}
		# 		cc_amount[cc] = row
		# for b in self.deductions:
		# 	cost_center, ba = frappe.db.get_value("Employee", b.employee, ["cost_center", "business_activity"])
		# 	cc = str(str(cost_center) + ":" + str(ba))
		# 	if cc in cc_amount:
		# 		cc_amount[cc]['deduction'] = flt(cc_amount[cc]['deduction'],2) + flt(b.amount,2)

		self.post_journal_entry()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")

	def before_cancel(self):
		je = frappe.db.sql("Select parent from `tabJournal Entry Account` where reference_type = 'PBVI' and reference_name = '{}' limit 1".format(self.name))
		if je:
			doc = frappe.get_doc("Journal Entry",je[0][0])
			if doc.docstatus != 2:
				frappe.throw("Cannot cancel this document as there exists journal entry against this document")

	def validate_duplicate(self):
		doc = frappe.db.sql("select name from tabPBVI where docstatus != 2 and fiscal_year = \'"+str(self.fiscal_year)+"\' and name != \'"+str(self.name)+"\'")		
		if doc:
			frappe.throw("Can not create multiple PBVI for the same year")

	def calculate_values(self):
		deductions = self.get_deductions()
		start = str(self.fiscal_year)+'-01-01'
		end   = str(self.fiscal_year)+'-12-31'
		days_in_year = date_diff(end, start)+1
		if self.items:
			tot = tax = net = ded = 0
			for a in self.items:
				
				# a.amount	= flt(a.total_basic_pay)*flt(self.pbvi_percent)/100
				a.amount = flt((flt(flt(a.pbvi_percent/100)*a.total_basic_pay)/days_in_year)*a.days_worked,2)
				a.tax_amount = flt(get_salary_tax(a.amount),2)
				a.deduction_amount = flt(deductions.get(a.employee))
				a.balance_amount = flt(a.amount,2) - flt(a.tax_amount,2) - flt(a.deduction_amount,2)
				tot += flt(a.amount,2)
				tax += flt(a.tax_amount,2)
				net += flt(a.balance_amount,2)
				ded += flt(a.deduction_amount,2)

			self.total_amount = tot
			self.tax_amount   = tax
			self.net_amount   = net
			self.total_deductions = ded

		else:
			frappe.throw("Cannot save without employee details")


	def get_deductions(self):
		deductions = {}
		for d in self.deductions:
			deductions[d.employee] = flt(d.amount) if d.employee not in deductions else deductions[d.employee] + flt(d.amount)
		return deductions

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
				"account": company_doc.pbvi_account,
				"debit_in_account_currency": item.get('net_amount'),
				"cost_center": key,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		if flt(self.tax_amount) > 0:
				accounts.append({
					"account": company_doc.salary_tax_account,
					"credit_in_account_currency": flt(self.tax_amount),
					"cost_center": self.cost_center,
					"reference_type": self.doctype,
					"reference_name": self.name
				})
		total_amount_in_words = money_in_words(self.net_amount)

		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"title": "{}% PBVI to Employee".format(self.pbvi_percent),
			"user_remark": "Note: {}% PBVI Payment to Employee".format(self.pbvi_percent),
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
		accounts.append({
			"account": company_doc.default_bank_account,
			"credit_in_account_currency": flt(self.net_amount,2),
			"cost_center": self.cost_center,
			"reference_type": self.doctype,
			"reference_name": self.name
		})
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"title": "{}% PBVI Payment to Employee".format(self.pbvi_percent),
			"user_remark": "Note: {}% PBVI Payment to Employee".format(self.pbvi_percent),
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.net_amount),
			"branch": self.branch,
			"accounts":accounts
		})
		je.insert()
		return je.name

	def tax_entry(self):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		accounts = []
		company_doc = frappe.get_doc("Company", self.company)
		accounts.append({
			"account": company_doc.default_bank_account,
			"credit_in_account_currency": flt(self.tax_amount,2),
			"cost_center": self.cost_center,
			"reference_type": self.doctype,
			"reference_name": self.name
		})
		if flt(self.tax_amount) > 0:
			accounts.append({
				"account": company_doc.salary_tax_account,
				"debit_in_account_currency": flt(self.tax_amount,2),
				"cost_center": self.cost_center,
				"reference_type": self.doctype,
				"reference_name": self.name
			})
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"title": "Tax Entry for {}% PBVI".format(self.pbvi_percent),
			"user_remark": "Note: Tax Entry for {}% PBVI Payment to Employee tax entry".format(self.pbvi_percent),
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.net_amount),
			"branch": self.branch,
			"accounts":accounts
		})
		je.insert()
		return je.name

	@frappe.whitelist()
	def get_pbvi_details(self):
		if not self.fiscal_year:
			frappe.throw("Fiscal Year is Mandatory")
		if not self.pbvi_percent:
			frappe.throw("PBVI percent is Mandatory")
		if self.pbvi_percent <= 0 :
			frappe.throw("PBVI percent cannot be 0 or less than 0")
		start = str(self.fiscal_year)+'-01-01'
		end   = str(self.fiscal_year)+'-12-31'
		days_in_year = date_diff(end, start)+1
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
		# 					and ss.eligible_for_pbvi = 1)
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
		# 			and ss.eligible_for_pbvi = 1)
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
		# 			and ss.eligible_for_pbvi = 1)
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
		# 				`tabPBVI Details` bd,
		# 				 `tabPBVI` b
		# 			where b.fiscal_year = '{0}'
		# 			and b.name <> '{4}'
		# 			and bd.parent = b.name
		# 			and bd.employee = e.employee
		# 			and b.docstatus in (0,1))
		# 		order by e.branch
		# 				""".format(self.fiscal_year, start, end, self.employee_status, self.name, self.pbvi_percent)
		query = """SELECT
						e.name as employee,
						e.employee_name,
						e.employment_type,
						e.branch,
						e.date_of_joining,
						e.relieving_date,
						e.salary_mode,
						e.division,
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
							FROM `tabPBVI Details` bd
							INNER JOIN `tabPBVI` b ON b.name <> '{4}' AND bd.parent = b.name AND bd.employee = e.employee AND b.docstatus IN (0,1)
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
		""".format(self.fiscal_year, start, end, self.employee_status, self.name, self.pbvi_percent)
		
		entries = frappe.db.sql(query, as_dict=True)
		self.set('items', [])

		start = getdate(start)
		end = getdate(end)
		for d in entries:
			# d.amount = 0
			row = self.append('items', {})
			total_leave_days = 0
			d.unit_rating = frappe.db.get_value(
       				"Performance Evaluation",
           			{
                  		"employee": frappe.db.get_value("Department", d.division, "approver"),
						"pms_calendar": self.fiscal_year
                    },
					"final_score_percent"
           )
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
			if frappe.db.get_value("Employee", d.employee, "pbvi_percent") == 0 or not frappe.db.get_value("Employee", d.employee, "pbvi_percent"):
				if not d.unit_rating or d.unit_rating == 0:
					d.unit_rating = flt(frappe.db.get_value("Department", d.department, "unit_rating"))
				d.unit_rating = 0 if not d.unit_rating else d.unit_rating * 0.5
				d.employee_rating = 0
				if employee_rating:
					d.employee_rating = employee_rating[0].final_score
				if not d.employee_rating:
					d.employee_rating = 0
				d.employee_rating = d.employee_rating * 0.5
				d.total_rating = d.unit_rating+d.employee_rating
				if frappe.db.get_single_value("HR Settings", "use_flat_pbvi") == 0:
					if self.company_achievement < 95:
						if d.total_rating < self.company_achievement:
							d.pbvi_percent = flt((d.total_rating/self.company_achievement)*(self.pbvi_percent),3)
						else:
							d.pbvi_percent = self.pbvi_percent
					else:
						if d.total_rating < 95:
							d.pbvi_percent = flt((d.total_rating/95)*(self.pbvi_percent),3)
						else:
							d.pbvi_percent = self.pbvi_percent
				else:
					d.pbvi_percent = flt(self.pbvi_percent, 3)
			else:
				d.pbvi_percent = flt(frappe.db.get_value("Employee", d.employee, "pbvi_percent"),3)

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
			if str(d.date_of_joining).split("-")[0] == str(self.fiscal_year) and flt(str(d.date_of_joining).split("-")[1]) < 10:
				d.days_worked = date_diff(datetime.strptime(str(self.fiscal_year)+"-12-31", "%Y-%m-%d").date(), add_days(datetime.strptime(str(self.fiscal_year)+"-"+str(int(str(d.date_of_joining).split("-")[1])+3)+"-"+str(d.date_of_joining).split("-")[2], "%Y-%m-%d").date(), 15))+1
				days_in_year = flt(date_diff(datetime.strptime(str(self.fiscal_year)+"-12-31", "%Y-%m-%d").date(), datetime.strptime(str(d.date_of_joining), "%Y-%m-%d").date()))
				d.no_probation = 0
			elif str(d.date_of_joining).split("-")[0] == str(self.fiscal_year) and flt(str(d.date_of_joining).split("-")[1]) >= 10:
				d.days_worked = 0
				d.no_probation = 0
			if str(d.date_of_joining).split("-")[0] == str(int(self.fiscal_year)-1) and flt(str(d.date_of_joining).split("-")[1]) > 9 and d.no_probation == 0:
				d.days_worked = date_diff(datetime.strptime(str(self.fiscal_year)+"-12-31", "%Y-%m-%d").date(), add_days(datetime.strptime(str(add_months(d.date_of_joining,3)), "%Y-%m-%d").date(), 15))+1
				days_in_year = flt(date_diff(datetime.strptime(str(self.fiscal_year)+"-12-31", "%Y-%m-%d").date(), datetime.strptime(str(self.fiscal_year)+"-01-01", "%Y-%m-%d").date()))+1
				if d.no_probation != 1:
					d.no_probation = 0
			if str(d.date_of_joining).split("-")[0] != str(int(self.fiscal_year)-1) and str(d.date_of_joining).split("-")[0] != str(self.fiscal_year):
				d.no_probation = 1

			d.days_worked = d.days_worked - total_leave_days
			if d.days_worked < 0:
				d.days_worked = 0
			# if d.status == 'Active':
				# if d.no_probation == 0:
				# else:
				# 	d.amount = flt(flt(flt(d.pbvi_percent/100)*d.total_basic_pay),2)
			d.amount = flt((flt(flt(d.pbvi_percent/100)*d.total_basic_pay)/days_in_year)*d.days_worked,2)
			# else:
			# 	d.amount = flt(flt(flt(d.pbvi_percent/100)*d.total_basic_pay),2)
			row.update(d)
			