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
		row = 1
		if self.items:
			tot = tax = net = ded = 0
			for a in self.items:
				if a.returning == 1:
					if str(a.date_of_joining).split("-")[0] != str(self.fiscal_year):
						frappe.throw("Employees returning from leave joining date for Employee {}({}) at row {} should be during fiscal year {}.".format(a.employee_name, a.employee, row, self.fiscal_year))
					a.days_worked = date_diff(getdate(str(self.fiscal_year)+"-12-31"), a.date_of_joining)+1
					if a.days_worked < 0:
						a.days_worked = 0
				# a.amount	= flt(a.total_basic_pay)*flt(self.pbvi_percent)/100
				if flt(days_in_year) != flt(a.days_worked):
					a.amount = flt(flt(flt(flt(flt(a.pbvi_percent,2)/100)*a.total_basic_pay,2)/days_in_year,2)*a.days_worked,2)
				else:
					a.amount = flt(flt(flt(a.pbvi_percent,2)/100)*a.total_basic_pay,2)
				a.tax_amount = flt(get_salary_tax(a.amount),2)
				a.deduction_amount = flt(deductions.get(a.employee))
				a.balance_amount = flt(a.amount,2) - flt(a.tax_amount,2) - flt(a.deduction_amount,2)
				tot += flt(a.amount,2)
				tax += flt(a.tax_amount,2)
				net += flt(a.balance_amount,2)
				ded += flt(a.deduction_amount,2)
				row += 1

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
		query = """SELECT
						e.name as employee,
						e.employee_name,
						e.employment_type,
						e.designation,
						e.branch,
						e.date_of_joining,
						e.relieving_date,
						e.salary_mode,
						e.division,
						e.bank_name,
						e.bank_ac_no,
						e.cost_center,
						e.reports_to,
						datediff(least(ifnull(e.relieving_date, '9999-12-31'), '{2}'), greatest(e.date_of_joining, '{1}')) + 1 AS days_worked,
						0 AS total_basic_pay
					FROM
						tabEmployee e
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
						days_worked
					ORDER BY
						e.branch;
		""".format(self.fiscal_year, start, end, self.employee_status, self.name, self.pbvi_percent)
		
		entries = frappe.db.sql(query, as_dict=True)
		self.set('items', [])

		start = getdate(start)
		end = getdate(end)
		for d in entries:
			# d.amount = 0
			d.basic_pay = 0
			row = self.append('items', {})
			total_leave_days = basic_pay = 0
			unit_rating = {}
			unit_rating_1 = {}
			unit_rating_2 = {}
			reports_to = []
			#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
			target_branch = frappe.db.sql("""
				select 1
				from `tabTarget Set Up` where docstatus = 1 and employee = '{}'
				and pms_calendar = '{}' and division like '%Branch Operations Division%'
			""".format(d.employee, self.fiscal_year))
			target_dep = frappe.db.sql("""
				select division
				from `tabTarget Set Up` where docstatus = 1 and employee = '{}'
				and pms_calendar = '{}'
			""".format(d.employee, self.fiscal_year),as_dict=1)
			if len(target_dep) > 0:
				for td in target_dep:
					reports_to.append(frappe.db.get_value("Department", target_dep, "approver"))
			if len(target_branch) > 0:
				target_branch = 1
			else:
				target_branch = 0
			#--------------------------------------------end----------------------------------------#
			if frappe.db.get_value("Department", d.division, "approver") == d.employee and d.designation != "Chief Executive Officer" and target_branch == 0:
				unit_rating = frappe.db.sql("""
										select count(name) as nos, sum(form_i_total_rating_100) as final_score
										from `tabPerformance Evaluation` where docstatus = 1 and employee in ({})
										and pms_calendar = '{}'
										""".format(", ".join("'"+sup+"'" for sup in reports_to), self.fiscal_year), as_dict = 1)
				
				# d.unit_rating = frappe.db.get_value(
				# 		"Performance Evaluation",
				# 		{
				# 			"employee": d.reports_to,
				# 			"pms_calendar": self.fiscal_year
				# 		},
				# 		"form_i_total_rating_100"
				# )
			elif frappe.db.get_value("Department", d.division, "approver") == d.employee and d.designation == "Chief Executive Officer" and target_branch == 0:
				# d.unit_rating = frappe.db.get_value(
				# 		"Performance Evaluation",
				# 		{
				# 			"employee": d.employee,
				# 			"pms_calendar": self.fiscal_year
				# 		},
				# 		"form_i_total_rating_100"
				# )
				unit_rating =frappe.db.sql("""
										select count(name) as nos, sum(form_i_total_rating_100) as final_score
										from `tabPerformance Evaluation` where docstatus = 1 and employee = '{}'
										and pms_calendar = '{}'
										""".format(d.employee, self.fiscal_year), as_dict = 1)
			#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
			elif target_branch == 1:
				# d.unit_rating = frappe.db.get_value(
				# 		"Performance Evaluation",
				# 		{
				# 			"employee": d.employee,
				# 			"pms_calendar": self.fiscal_year
				# 		},
				# 		"form_i_total_rating_100"
				# )
				unit_rating_1 =frappe.db.sql("""
										select count(name) as nos, sum(form_i_total_rating_100) as final_score
										from `tabPerformance Evaluation` where docstatus = 1 and employee = '{}'
										and pms_calendar = '{}'
										""".format("1045", self.fiscal_year), as_dict = 1)
				unit_rating_2 =frappe.db.sql("""
										select count(name) as nos, sum(form_i_total_rating_100) as final_score
										from `tabPerformance Evaluation` where docstatus = 1 and employee = '{}'
										and pms_calendar = '{}'
										""".format("0043", self.fiscal_year), as_dict = 1)
			#--------------------------------------------end----------------------------------------#
			else:
				# d.unit_rating = frappe.db.get_value(
				# 		"Performance Evaluation",
				# 		{
				# 			"employee": frappe.db.get_value("Department", d.division, "approver"),
				# 			"pms_calendar": self.fiscal_year
				# 		},
				# 		"form_i_total_rating_100"
				# )
				unit_rating =frappe.db.sql("""
										select count(name) as nos, sum(form_i_total_rating_100) as final_score
										from `tabPerformance Evaluation` where docstatus = 1 and employee = '{}'
										and pms_calendar = '{}'
										""".format(d.employee, self.fiscal_year), as_dict = 1)
			# 	d.employee_rating =frappe.db.get_value(
			# 			"Performance Evaluation",
			#    			{
			#           		"employee": d.employee,
			# 				"pms_calendar": self.fiscal_year
			#             },
			# 			"final_score_percent"
			#    )
			if frappe.db.exists("Salary Slip", {"employee":d.employee, "fiscal_year": self.fiscal_year}):
				basic_pay = frappe.db.sql("""select sd.amount as basic_pay from `tabSalary Slip` ss, `tabSalary Detail` sd
							  where sd.parent = ss.name and sd.salary_component = 'Basic Pay' and ss.docstatus = 1
							  and ss.fiscal_year = '{}' and ss.employee = '{}' order by month desc limit 1""".format(self.fiscal_year, d.employee),as_dict=1)
				if len(basic_pay) > 0:
					d.basic_pay = flt(basic_pay[0].basic_pay,2)
			employee_rating =frappe.db.sql("""
                                    select count(name) as nos, sum(final_score_percent) as final_score
                                    from `tabPerformance Evaluation` where docstatus = 1 and employee = '{}'
                                    and pms_calendar = '{}'
                                    """.format(d.employee, self.fiscal_year), as_dict = 1)
			if target_branch == 0:#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
				if unit_rating[0].final_score:
					d.unit_rating = unit_rating[0].final_score/unit_rating[0].nos
				else:
					d.unit_rating = 0
			else:#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
				if unit_rating_1[0].final_score:#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
					unit_rating_1 = flt(unit_rating_1[0].final_score)/flt(unit_rating_1[0].nos)#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
				else:#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
					unit_rating_1 = 0#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
				if unit_rating_2[0].final_score:#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
					unit_rating_2 = (flt(unit_rating_2[0].final_score)/flt(unit_rating_2[0].nos))#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
				else:#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
					unit_rating_2 = 0#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
				d.unit_rating = flt(unit_rating_1 * 0.5,2)+flt(unit_rating_2 * 0.5,2)#--------for pbva payout for fiscal year 2024 only / remove after use ------------------#
			if frappe.db.get_value("Employee", d.employee, "pbvi_percent") == 0 or not frappe.db.get_value("Employee", d.employee, "pbvi_percent"):
				if not d.unit_rating or d.unit_rating == 0:
					d.unit_rating = flt(frappe.db.get_value("Department", d.department, "unit_rating"))
				d.unit_rating = 0 if not d.unit_rating else flt(d.unit_rating * 0.5,2)
				d.employee_rating = 0
				if employee_rating[0].final_score:
					d.employee_rating = employee_rating[0].final_score/employee_rating[0].nos
				if not d.employee_rating:
					d.employee_rating = 0
				if d.employee_rating < flt(75):
					d.employee_rating = 0
					d.unit_rating = 0
				d.employee_rating = flt(d.employee_rating * 0.5,2)
				d.total_rating = flt(d.unit_rating+d.employee_rating,2)
				if frappe.db.get_single_value("HR Settings", "use_flat_pbvi") == 0:
					if self.company_achievement < 95:
						if d.total_rating < 95:
							d.pbvi_percent = flt((d.total_rating/95)*(self.pbvi_percent),3)
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
			
			no_months = 0
			if str(d.date_of_joining).split("-")[0] == self.fiscal_year:
				if d.relieving_date:
					if str(d.relieving_date).split("-")[0] == self.fiscal_year:
						no_months = int(str(d.relieving_date).split("-")[1])-int(str(d.date_of_joining).split("-")[1])+1
					elif str(d.relieving_date).split("-")[0] > self.fiscal_year:
						no_months = 12 - int(str(d.date_of_joining).split("-")[1])+1
				else:
					no_months = 12 - int(str(d.date_of_joining).split("-")[1])+1
			else:
				no_months = 12
			# d.total_basic_pay = 0 if not d.total_basic_pay else d.total_basic_pay
			d.total_basic_pay = d.basic_pay * no_months
			days_in_year = date_diff(end, start)+1
			total_leave_days = frappe.db.sql("select sum(ifnull(total_leave_days,0)) as leaves from `tabLeave Application` where docstatus = 1 and employee = '{}' and year(from_date) = '{}' and leave_type not in ('Study Leave', 'EOL')".format(d.employee, self.fiscal_year), as_dict=1)

			# if len(total_leave_days) > 0:
			# 	total_leave_days = total_leave_days[0].leaves
			# else:
			# 	total_leave_days = 0
			# if not total_leave_days:
			# 	total_leave_days = 0
			# if flt(total_leave_days) > 30:
			# 	total_leave_days -= 30
			# else:
			total_leave_days = 0
			if str(d.date_of_joining).split("-")[0] == str(self.fiscal_year) and flt(str(d.date_of_joining).split("-")[1]) < 10:
				d.days_worked = date_diff(datetime.strptime(str(self.fiscal_year)+"-12-31", "%Y-%m-%d").date(), add_days(datetime.strptime(str(self.fiscal_year)+"-"+str(int(str(d.date_of_joining).split("-")[1])+3)+"-"+str(d.date_of_joining).split("-")[2], "%Y-%m-%d").date(), 15))+1
				days_in_year = flt(date_diff(datetime.strptime(str(self.fiscal_year)+"-12-31", "%Y-%m-%d").date(), datetime.strptime(str(d.date_of_joining), "%Y-%m-%d").date()))+1
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
			# if d.employee == "1041":
			# 	frappe.throw("Days in Year: "+str(days_in_year)+" Days Worked"+str(d.days_worked)+" Total Basic Pay: "+str(d.total_basic_pay)+" PBVA Amount: "+str(flt((flt(flt(d.pbvi_percent/100)*d.total_basic_pay)/days_in_year)*d.days_worked,2)))
			if flt(days_in_year) != flt(d.days_worked):
				d.amount = flt(flt(flt(flt(flt(d.pbvi_percent,2)/100)*d.total_basic_pay,2)/days_in_year,2)*d.days_worked,2)
			else:
				d.amount = flt(flt(flt(d.pbvi_percent,2)/100)*d.total_basic_pay,2)
			# if d.employee == "1041":
			# 	frappe.throw(str(d.amount)+" "+str(flt(d.pbvi_percent,2)))
			# else:
			# 	d.amount = flt(flt(flt(d.pbvi_percent/100)*d.total_basic_pay),2)
			row.update(d)
			