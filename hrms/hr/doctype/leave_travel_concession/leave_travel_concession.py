# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, cint, date_diff
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta

class LeaveTravelConcession(Document):
	def validate(self):
		self.validate_employee()
		self.validate_duplicate()
		self.calculate_values()

	def on_submit(self):
		cc_amount = {}
		for a in self.items:
			cost_center, ba = frappe.db.get_value("Employee", a.employee, ["cost_center", "business_activity"])
			cc = str(str(cost_center) + ":" + str(ba))
			# this below code is copied from BTL
			if cc in cc_amount:
				cc_amount[cc] = cc_amount[cc] + a.amount
			else:
				cc_amount[cc] = a.amount
				
		self.post_journal_entry(cc_amount)
	def validate_employee(self):
		if self.employee:
			employment_type = frappe.db.get_value("Employee",self.employee,"employment_status")
			joining_date = frappe.db.get_value("Employee",self.employee,"date_of_joining")
			working_days =date_diff(self.posting_date,joining_date)
			if employment_type == "Probation":
				frappe.throw("Employee who is in Probation Period is not eligible for LTC.")
			if working_days < 360 :
				frappe.throw("Employee who did not serve 1 year is not eligible for LTC")

	def validate_duplicate(self):
		emp_list = ", ".join("'"+a.employee+"'" for a in self.items)
		doc = frappe.db.sql("""select 
						a.name 
					from 
						`tabLeave Travel Concession` a,
						`tabLTC Details` b 
					where
						a.name = b.parent
						and a.docstatus = 1 
						and a.fiscal_year = \'"+str(self.fiscal_year)+"\' 
						and a.name != \'"+str(self.name)+"\'
						and b.employee in ({})""".format(emp_list))		
		if doc:
			frappe.throw("Cannot create multiple LTC for the same year. One or more employees LTC already processed.")

	def calculate_values(self):
		if self.items:
			total = 0
			for a in self.items:
				total += flt(a.amount)
			self.total_amount = total
		else:
			frappe.throw("Cannot save without any employee records")

	def post_journal_entry(self, cc_amount):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1 
		je.title = "LTC for " + self.branch + "(" + self.name + ")"
		je.voucher_type = 'Bank Entry'
		je.naming_series = 'Bank Payment Voucher'
		je.remark = 'LTC payment against : ' + self.name
		je.posting_date = self.posting_date
		je.branch = self.branch
		company = "State Mining Corporation Ltd"
		ltc_account = frappe.db.get_value("Company",company,"ltc_account")
		if not ltc_account:
			frappe.throw("Setup LTC Account in HR Accounts Settings")
		expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		
		if not expense_bank_account:
			frappe.throw("Setup Expense Bank Account in Branch")
		total_credit = 0
		for key in cc_amount.keys():
			values = key.split(":")
			je.append("accounts", {
					"account": ltc_account,
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": values[0],
					"business_activity": values[1],
					"debit_in_account_currency": flt(cc_amount[key],2),
					"debit": flt(cc_amount[key],2),
				})
			total_credit += flt(cc_amount[key])
		
		je.append("accounts", {
				"account": expense_bank_account,
				"cost_center": frappe.db.get_value("Branch",self.branch,"cost_center"),
				"business_activity": "Common",
				"credit_in_account_currency": total_credit,
				"credit": total_credit,
				"reference_type": self.doctype,
				"reference_name": self.name,
			})

		je.insert()

		self.db_set("journal_entry", je.name)

	def on_cancel(self):
		jv = frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus")
		if jv != 2:
			frappe.throw("Can not cancel LTC without canceling the corresponding journal entry " + str(self.journal_entry))
		else:
			self.db_set("journal_entry", None)


	@frappe.whitelist()
	def get_ltc_details(self):
		start, end = frappe.db.get_value("Fiscal Year", self.fiscal_year, ["year_start_date", "year_end_date"])
		entries = frappe.db.sql("""select 
						e.date_of_joining, 
						b.employee, 
						b.employee_name, 
						b.branch, 
						a.amount, 
						e.bank_name, 
						e.bank_ac_no  
					from 
						`tabSalary Detail` a, 
						`tabSalary Structure` b, 
						`tabEmployee` e 
					where 
						a.parent = b.name 
						and b.employee = e.name 
						and a.salary_component = 'Basic Pay' 
						and (b.is_active = 'Yes' or e.relieving_date between \'"+str(start)+"\' and \'"+str(end)+"\') 
						and b.eligible_for_ltc = 1 
					order by b.branch """, as_dict=True)
		self.set('items', [])
		for d in entries:
			d.basic_pay = d.amount
			month_start = datetime.strptime(str(d.date_of_joining).split("-")[0]+"-"+str(d.date_of_joining).split("-")[1]+"-01","%Y-%m-%d")
			dates = calendar.monthrange(month_start.year, month_start.month)[1]
			working_days =date_diff(self.posting_date,d.date_of_joining)
			if working_days >= 360 :
				if getdate(str(self.fiscal_year) + "-01-01") < getdate(d.date_of_joining) <  getdate(str(self.fiscal_year) + "-12-31"):
					if cint(str(d.date_of_joining)[8:10]) < 15:
						months = 12 - cint(str(d.date_of_joining)[5:7]) + 1
					else:
						months = 12 - cint(str(d.date_of_joining)[5:7])
					
					amount = d.amount
					if flt(d.amount) > 15000:
						amount = 15000

					d.amount = round(flt((flt(months)/12.0) * amount), 2)
					days = relativedelta(datetime.strptime(str(d.date_of_joining).split("-")[0]+"-"+str(d.date_of_joining).split("-")[1]+"-"+str(dates),"%Y-%m-%d"),datetime.strptime(str(d.date_of_joining),"%Y-%m-%d")).days
					if int(days) < int(dates):
						d.amount += round(flt((flt(days)/12.0/30.0) * amount), 2)

				else:
					if flt(d.amount) > 15000:
						d.amount = 15000
				row = self.append('items', {})
				row.update(d)


