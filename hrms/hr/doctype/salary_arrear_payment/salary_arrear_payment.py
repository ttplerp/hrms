# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, flt, nowdate, get_first_day, get_last_day
from hrms.hr.hr_custom_functions import get_month_details, get_payroll_settings, get_salary_tax
from erpnext.accounts.doctype.accounts_settings.accounts_settings import get_bank_account
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba
from frappe.model.document import Document
from datetime import datetime
import math

class SalaryArrearPayment(Document):
	def validate(self):
		self.total_net_arrear_payable = 0
		for a in self.items:
			self.total_net_arrear_payable += a.net_payable_arrear
	@frappe.whitelist()
	# Populate Employee details 
	def get_employees(self):
		if not self.from_month:
			frappe.throw("Please set Effective From Month")
		if not self.fiscal_year:
			frappe.throw(_("<b>Fiscal Year</b> is Mandatory"))

		year_start_date = str(self.fiscal_year)+'-01-01'
		year_end_date = str(self.fiscal_year)+'-12-31'
		
		cond = ""
		# if self.employee_status == 'Active':
		# 	cond += "and e.date_of_joining <= '{year_end_date}' and ifnull(e.relieving_date,'9999-12-31') > \
		# 		'{year_end_date}'".format(year_end_date=year_end_date)
		# elif self.employee_status == 'Left':
		# 	cond += "and ifnull(e.relieving_date,'9999-12-31') between '{year_start_date}' and '{year_end_date}'"\
		# 		.format(year_start_date=year_start_date, year_end_date=year_end_date)
		# else:
		# 	cond += "and e.date_of_joining <= '{year_end_date}' and ifnull(e.relieving_date,'9999-12-31') >= \
		# 		'{year_start_date}'".format(year_start_date=year_start_date,year_end_date=year_end_date)

		month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(self.from_month) + 1
		month = str(month) if cint(month) > 9 else str("0" + str(month))
		query = """select ss.name as salary_slip, e.name as employee, e.employee_name, e.branch, (select salary_structure from `tabSalary Slip Item` ssi where ssi.parent = ss.name) as salary_struct,
				(select total_days_in_month from `tabSalary Slip Item` ssi where ssi.parent = ss.name) as total_days,
				(select	working_days from `tabSalary Slip Item` ssi where ssi.parent = ss.name) as working_days,
				e.bank_name, e.bank_ac_no, ss.employer_pf as previous_employer_pf, ss.fiscal_year as ss_year, ss.month as ss_month,
				ss.employer_pf as previous_pf,
				(
					select eg.employee_pf from `tabEmployee Group` eg where eg.name = e.employee_group
				) as pf_per,
				(
					select eg.employer_pf from `tabEmployee Group` eg where eg.name = e.employee_group
				) as employer_pf_per,
				(
					select eg.health_contribution from `tabEmployee Group` eg where eg.name = e.employee_group
				) as health_con_per,
				(
					select sd.amount from `tabSalary Detail` sd where sd.parent = ss.name
					and sd.salary_component = 'Basic Pay'
				) as prev_basic_pay,
				ifnull((
					select sd.amount from `tabSalary Detail` sd where sd.parent = ss.name
					and sd.salary_component = 'Officiating Allowance'
				),0) as prev_officiating,
				ifnull((
					select sd.amount from `tabSalary Detail` sd where sd.parent = ss.name
					and sd.salary_component = 'Contract Allowance'
				),0) as prev_contract,
				ifnull((
					select sd.amount from `tabSalary Detail` sd where sd.parent = ss.name
					and sd.salary_component = 'Corporate Allowance'
				),0) as prev_corporate,
				ifnull((
					select sd.amount from `tabSalary Detail` sd where sd.parent = ss.name
					and sd.salary_component = 'MPI'
				),0) as prev_mpi,
				ifnull((
					select sd.amount from `tabSalary Detail` sd where sd.parent = ss.name
					and sd.salary_component = 'PF'
				),0) as previous_pf,
				ifnull((
					select sd.amount from `tabSalary Detail` sd where sd.parent = ss.name
					and sd.salary_component = 'Salary Tax'
				),0) as previous_salary_tax,
				ifnull((
					select sd.amount from `tabSalary Detail` sd where sd.parent = ss.name
					and sd.salary_component = 'Health Contribution'
				),0) as prev_hc
			from tabEmployee e, `tabSalary Slip` ss
			where not exists(select 1
				from `tabSalary Arrear Payment Item` sapi, `tabSalary Arrear Payment` sap
				where sap.fiscal_year = '{fiscal_year}'
				and sap.name != '{name}' and sapi.parent = sap.name
				and sapi.employee = e.employee and sap.docstatus != 2)
			and ss.employee = e.name and ss.month = '{month}' and ss.fiscal_year = '{fiscal_year}'
			and ss.docstatus = 1
			order by e.name
			""".format(fiscal_year=self.fiscal_year, cond=cond, year_start_date=year_start_date, \
				year_end_date=year_end_date, status=self.employment_status, name=self.name, month=month)
		
		entries = frappe.db.sql(query, as_dict=True)
		self.set('items', [])
		for d in entries:
			if not d.salary_struct:
				frappe.throw(d.employee)
			emp_doc = frappe.get_doc("Employee", d.employee)
			sal_struct = frappe.get_doc("Salary Structure",d.salary_struct)
			d.new_minimum_basic_pay, d.fixed_allowance = frappe.db.get_value("Employee Grade", emp_doc.grade, ["lower_limit","fixed_allowance"])
			if d.employee == "202010218":
				start_date = datetime.strptime(str(get_first_day(str(d.ss_year)+"-"+str(d.ss_month)+"-01")).split(" ")[0],"%Y-%m-%d")
				end_date = datetime.strptime(str(get_last_day(str(d.ss_year)+"-"+str(d.ss_month)+"-01")).split(" ")[0],"%Y-%m-%d")
				total_days = end_date - start_date
				d.fixed_allowance = flt(flt(d.fixed_allowance) * (flt(d.working_days)/(flt(total_days.days)+1)),0)
			row = self.append('items', {})
			d.contract_allowance = d.corporate_allowance = d.mpi = d.officiating_allowance = 0
			if emp_doc.employment_type == "Contract":
				if emp_doc.grade in ("S1","S2","S3","O1","O2","O3","O4","O5","O6","O7","GS1","GS2","ESP"):
					d.basic_pay = flt(d.prev_basic_pay + d.prev_basic_pay * 0.05,0)
				else:
					d.basic_pay = flt(d.prev_basic_pay + d.prev_basic_pay * 0.02,0)
				d.basic_pay = math.ceil(d.basic_pay)
				if flt(str(d.basic_pay)[len(str(d.basic_pay))-1]) > 0 and flt(str(d.basic_pay)[len(str(d.basic_pay))-1]) <= 5:
					d.basic_pay = flt(str(d.basic_pay)[0:len(str(d.basic_pay))-1]+"5")
				elif flt(str(d.basic_pay)[len(str(d.basic_pay))-1]) > 5 and flt(str(d.basic_pay)[len(str(d.basic_pay))-1]) <= 9:
					value_to_add = 10 - flt(str(d.basic_pay)[len(str(d.basic_pay))-1])
					d.basic_pay = d.basic_pay + value_to_add
				if sal_struct.contract_allowance_method == "Percent":
					d.contract_allowance = flt(d.basic_pay*(sal_struct.contract_allowance*0.01),0)
				elif sal_struct.contract_allowance_method == "Lumpsum":
					d.contract_allowance = flt(sal_struct.contract_allowance)
				# d.new_minimum_basic_pay = flt(current_min_basic + current_min_basic * 0.02,0)
			else:
				if emp_doc.grade in ("M3","M2","M1","E3","E2","E1"):
					d.basic_pay = flt(d.prev_basic_pay + d.prev_basic_pay * 0.02,0)
				else:
					d.basic_pay = flt(d.prev_basic_pay + d.prev_basic_pay * 0.05,0)
				d.basic_pay = math.ceil(d.basic_pay)
				if flt(str(d.basic_pay)[len(str(d.basic_pay))-1]) > 0 and flt(str(d.basic_pay)[len(str(d.basic_pay))-1]) <= 5:
					d.basic_pay = flt(str(d.basic_pay)[0:len(str(d.basic_pay))-1]+"5")
				elif flt(str(d.basic_pay)[len(str(d.basic_pay))-1]) > 5 and flt(str(d.basic_pay)[len(str(d.basic_pay))-1]) <= 9:
					value_to_add = 10 - flt(str(d.basic_pay)[len(str(d.basic_pay))-1])
					d.basic_pay = d.basic_pay + value_to_add
				if sal_struct.ca_method == "Percent":
					d.corporate_allowance = flt(d.basic_pay*(sal_struct.ca*0.01),0)
				elif sal_struct.ca_method == "Lumpsum":
					d.corporate_allowance = flt(sal_struct.ca)
			if d.prev_officiating > 0:
				if sal_struct.officiating_allowance_method == "Percent":
					d.corporate_allowance = flt(d.basic_pay*(sal_struct.officiating_allowance*0.01),0)
				elif sal_struct.officiating_allowance_method == "Lumpsum":
					d.corporate_allowance = flt(sal_struct.officiating_allowance)
			if d.prev_mpi > 0:
				if sal_struct.mpi_method == "Percent":
					d.mpi = flt(d.basic_pay*(sal_struct.mpi*0.01),0)
				elif sal_struct.officiating_allowance_method == "Lumpsum":
					d.mpi = flt(sal_struct.mpi)
			d.pf = flt(d.basic_pay * (d.pf_per * 0.01),0)
			d.employer_pf = flt(d.basic_pay * (d.employer_pf_per * 0.01),0)
			d.arrear_basic_pay = d.basic_pay - d.prev_basic_pay
			d.arrear_corporate_allowance = d.corporate_allowance - d.prev_corporate
			d.arrear_contract_allowance = d.contract_allowance - d.prev_contract
			d.arrear_officiating_allowance = d.officiating_allowance - d.prev_officiating
			d.arrear_mpi = d.mpi - d.prev_mpi
			d.new_gross_pay = flt(d.arrear_basic_pay + d.arrear_corporate_allowance + d.arrear_contract_allowance + d.arrear_officiating_allowance + d.arrear_mpi + d.fixed_allowance)
			if d.employee in ("202304478","202010218"):
				d.salary_tax = 0
				d.arrear_salary_tax = 0
				d.arrear_pf = 0
				d.arrear_employer_pf = 0
			else:
				d.salary_tax = get_salary_tax((d.basic_pay+d.corporate_allowance+d.contract_allowance+d.officiating_allowance+d.fixed_allowance+d.mpi-d.pf))
				d.arrear_pf = flt(d.pf-d.previous_pf)
				d.arrear_salary_tax = get_salary_tax(d.new_gross_pay-d.arrear_pf)
				d.arrear_employer_pf = flt(d.employer_pf-d.previous_employer_pf)
			d.health_contribution = flt((d.basic_pay+d.corporate_allowance+d.contract_allowance+d.officiating_allowance+d.mpi+d.fixed_allowance) * (d.health_con_per * 0.01),0)
			d.new_gross_pay = flt(d.arrear_basic_pay + d.arrear_corporate_allowance + d.arrear_contract_allowance + d.arrear_officiating_allowance + d.arrear_mpi + d.fixed_allowance)
			d.arrear_hc = flt(d.new_gross_pay*(d.health_con_per*0.01),0)
			d.total_deduction = flt(d.arrear_hc+d.arrear_pf+d.arrear_salary_tax)
			d.net_payable_arrear = d.new_gross_pay - d.total_deduction


			# d.months_in_service = flt(self.get_months(from_date, to_date),2)
			row.update(d)
		# self.calculate_values()
	@frappe.whitelist()
	def make_accounting_entry(self):
		"""
			---------------------------------------------------------------------------------
			type            Dr            Cr               voucher_type
			------------    ------------  -------------    ----------------------------------
			to payables     earnings      deductions       journal entry (journal voucher)
							  net pay
			to bank         net pay       bank             bank entry (bank payment voucher)
			remittance      deductions    bank             bank entry (bank payment voucher)
			---------------------------------------------------------------------------------
		"""
		if frappe.db.exists("Journal Entry", {"reference_type": self.doctype, "reference_name": self.name}):
			frappe.msgprint(_("Accounting Entries already posted"))
			return
		month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(self.from_month) + 1
		month = str(month) if cint(month) > 9 else str("0" + str(month))

		# Default Accounts
		default_bank_account = get_bank_account(self.branch)
		default_payable_account = frappe.db.get_value("Company", self.company,"salary_payable_account")
		company_cc              = frappe.db.get_value("Company", self.company,"company_cost_center")
		default_gpf_account     = frappe.db.get_value("Company", self.company, "employer_contribution_to_pf")
		default_business_activity = get_default_ba()
		salary_component_pf     = "PF"
		# cbs_enabled = frappe.db.exists('Company', {'cbs_enabled': 1})

		if not default_bank_account:
			frappe.throw(_("Default Bank Account is mandatory"))
		elif not default_payable_account:
			frappe.throw(_("Default Payable Account is mandatory"))
		elif not company_cc:
			frappe.throw(_("Default Company Cost Center is missing"))
		elif not default_gpf_account:
			frappe.throw(_("Default GPF account is mandatory"))
		
		# Salary Details
		cc = {}
		health_contribution = employee_pf = salary_tax = net_payable = 0
		for det in self.items:
			health_contribution += det.arrear_hc
			employee_pf += det.arrear_pf
			salary_tax += det.arrear_salary_tax
			net_payable += det.net_payable_arrear
			cost_center = frappe.db.get_value("Branch", det.branch, "cost_center")
			if cost_center not in cc:
				cc.update({
        			cost_center: {
               			"basic_pay": det.arrear_basic_pay,
                  		"corporate_allowance": det.arrear_corporate_allowance,
						"contract_allowance": det.arrear_contract_allowance,
						"officiating_allowance": det.arrear_officiating_allowance,
						"fixed_allowance": det.fixed_allowance,
						"mpi": det.arrear_mpi,
						"employer_pf": det.arrear_employer_pf
                    }
           		})
			else:
				cc[cost_center]['basic_pay'] += det.arrear_basic_pay
				cc[cost_center]['corporate_allowance'] += det.arrear_corporate_allowance
				cc[cost_center]['contract_allowance'] += det.arrear_contract_allowance
				cc[cost_center]['officiating_allowance'] += det.arrear_officiating_allowance
				cc[cost_center]['fixed_allowance'] += det.fixed_allowance
				cc[cost_center]['mpi'] += det.arrear_mpi
				cc[cost_center]['employer_pf'] += det.arrear_employer_pf

		posting        = frappe._dict()
		cc_wise_totals = frappe._dict()
		tot_payable_amt= 0
		#Payables Journal Entry -----------------------------------------------
		payables_je = frappe.new_doc("Journal Entry")
		payables_je.voucher_type= "Journal Entry"
		payables_je.naming_series = "Journal Voucher"
		payables_je.title = "Salary Arrear "+str(self.fiscal_year)+str(month)+" - To Payables"
		payables_je.remark =  "Salary Arrear "+str(self.fiscal_year)+str(month)+" - To Payables"
		payables_je.posting_date = nowdate()               
		payables_je.company = self.company
		payables_je.branch = self.branch
		payables_je.reference_type = self.doctype
		payables_je.reference_name =  self.name
		total_basic_pay = total_allowance = 0
		total_debit = total_credit = 0
		for rec in cc:
			payables_je.append("accounts", {
					"account": frappe.db.get_value("Salary Component", "Basic Pay", "gl_head"),
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": rec,
					"business_activity": default_business_activity,
					"debit_in_account_currency": flt(cc[rec]['basic_pay'],2),
					"debit": flt(cc[rec]['basic_pay'],2),
				})
			total_basic_pay += flt(cc[rec]['basic_pay'],2)
			total_debit += flt(cc[rec]['basic_pay'],2)
			payables_je.append("accounts", {
					"account": "Allowances - SMCL",
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": rec,
					"business_activity": default_business_activity,
					"debit_in_account_currency": flt(cc[rec]['corporate_allowance'],2)+flt(cc[rec]['contract_allowance'],2)+flt(cc[rec]['officiating_allowance'],2)+flt(cc[rec]['mpi'])+flt(cc[rec]['fixed_allowance'],2),
					"debit": flt(cc[rec]['corporate_allowance'],2)+flt(cc[rec]['contract_allowance'],2)+flt(cc[rec]['officiating_allowance'],2)+flt(cc[rec]['mpi'],2)+flt(cc[rec]['fixed_allowance'],2),
				})
			#Total Allowance
			total_allowance += flt(cc[rec]['corporate_allowance'],2)+flt(cc[rec]['contract_allowance'],2)+flt(cc[rec]['officiating_allowance'],2)+flt(cc[rec]['mpi'],2)+flt(cc[rec]['fixed_allowance'],2)
			#Fixed Allowance
			# payables_je.append("accounts", {
			# 		"account": frappe.db.get_value("Salary Component", "Fixed Allowance", "gl_head"),
			# 		"reference_type": self.doctype,
			# 		"reference_name": self.name,
			# 		"cost_center": rec,
			# 		"business_activity": default_business_activity,
			# 		"debit_in_account_currency": flt(cc[rec]['fixed_allowance'],2),
			# 		"debit": flt(cc[rec]['fixed_allowance'],2),
			# 	})
			# total_debit += flt(cc[rec]['fixed_allowance'],2)
			#Total Allowance
		#Health Contribution
		# frappe.throw(str(total_basic_pay+total_allowance))
		payables_je.append("accounts", {
				"account": frappe.db.get_value("Salary Component", "Health Contribution", "gl_head"),
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"business_activity": default_business_activity,
				"credit_in_account_currency": flt(health_contribution,2),
				"credit": flt(health_contribution,2),
				"party_check": 0
			})
		total_credit += flt(health_contribution,2)
		#PF
		payables_je.append("accounts", {
				"account": frappe.db.get_value("Salary Component", "PF", "gl_head"),
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"business_activity": default_business_activity,
				"credit_in_account_currency": flt(employee_pf,2),
				"credit": flt(employee_pf,2),
				"party_check": 0
			})
		total_credit += flt(employee_pf,2)
		#Salary Tax
		if salary_tax > 0:
			payables_je.append("accounts", {
					"account": frappe.db.get_value("Salary Component", "Salary Tax", "gl_head"),
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": company_cc,
					"business_activity": default_business_activity,
					"credit_in_account_currency": flt(salary_tax,2),
					"credit": flt(salary_tax,2),
				})
		total_credit += flt(salary_tax,2)
		#Salary Payble
		payables_je.append("accounts", {
				"account": default_payable_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"business_activity": default_business_activity,
				"credit_in_account_currency": flt(net_payable,2),
				"credit": flt(net_payable,2),
				"party_check": 0
			})
		total_credit += flt(net_payable,2)
		payables_je.flags.ignore_permissions = 1
		payables_je.total_debit = total_debit
		payables_je.total_credit = total_credit
		payables_je.insert()
		payables_je.submit()
		#Payables JE End -----------------------------------------------------
		#Salary Tax and HC Bank Entry -----------------------------------------------
		sthc_je = frappe.new_doc("Journal Entry")
		sthc_je.voucher_type= "Bank Entry"
		sthc_je.naming_series = "Bank Payment Voucher"
		sthc_je.title = "Arrear Salary Tax and HC for "+self.from_month
		sthc_je.remark =  "Arrear Salary Tax and HC for "+self.from_month
		sthc_je.posting_date = nowdate()               
		sthc_je.company = self.company
		sthc_je.branch = self.branch
		sthc_je.reference_type = self.doctype
		sthc_je.reference_name =  self.name
		#Health Contribution
		sthc_je.append("accounts", {
				"account": frappe.db.get_value("Salary Component", "Health Contribution", "gl_head"),
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"business_activity": default_business_activity,
				"debit_in_account_currency": flt(health_contribution,2),
				"debit": flt(health_contribution,2),
				"party_check": 0
			})
		#Salary Tax
		if salary_tax > 0:
			sthc_je.append("accounts", {
					"account": frappe.db.get_value("Salary Component", "Salary Tax", "gl_head"),
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": company_cc,
					"business_activity": default_business_activity,
					"debit_in_account_currency": flt(salary_tax,2),
					"debit": flt(salary_tax,2),
				})
		#To Bank Account
		sthc_je.append("accounts", {
				"account": default_bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"business_activity": default_business_activity,
				"credit_in_account_currency": flt(salary_tax,2)+flt(health_contribution,2),
				"credit": flt(salary_tax,2)+flt(health_contribution,2),
			})

		sthc_je.flags.ignore_permissions = 1 
		sthc_je.insert()
		#Salary Tax and HC Bank Entry End -----------------------------------------------

		#PF Bank Entry -----------------------------------------------
		pf_je = frappe.new_doc("Journal Entry")
		pf_je.voucher_type= "Bank Entry"
		pf_je.naming_series = "Bank Payment Voucher"
		pf_je.title = "Arrear PF contribution of SMCL staff for the month of "+self.from_month
		pf_je.remark =  "Arrear PF contribution of SMCL staff for the month of "+self.from_month
		pf_je.posting_date = nowdate()               
		pf_je.company = self.company
		pf_je.branch = self.branch
		pf_je.reference_type = self.doctype
		pf_je.reference_name =  self.name
		#Employer PF Expense
		total_employer_pf = 0
		for p in cc:
			pf_je.append("accounts", {
					"account": default_gpf_account,
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": p,
					"business_activity": default_business_activity,
					"debit_in_account_currency": flt(cc[p]['employer_pf'],2),
					"debit": flt(cc[p]['employer_pf'],2),
				})
			total_employer_pf += flt(cc[p]['employer_pf'],2)
		#Employee PF
		pf_je.append("accounts", {
				"account": frappe.db.get_value("Salary Component", "PF", "gl_head"),
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"business_activity": default_business_activity,
				"debit_in_account_currency": flt(employee_pf,2),
				"debit": flt(employee_pf,2),
				"party_check": 0
			})
		#To Bank Account
		pf_je.append("accounts", {
				"account": default_bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"business_activity": default_business_activity,
				"credit_in_account_currency": flt(employee_pf,2)+flt(total_employer_pf,2),
				"credit": flt(employee_pf,2)+flt(total_employer_pf,2),
			})

		pf_je.flags.ignore_permissions = 1 
		pf_je.insert()
		#PF Bank Entry End -----------------------------------------------

		#Payables to Bank Entry -----------------------------------------------
		pb_je = frappe.new_doc("Journal Entry")
		pb_je.voucher_type= "Bank Entry"
		pb_je.naming_series = "Bank Payment Voucher"
		pb_je.title = "Salary Arrear paid for the month of "+self.from_month
		pb_je.remark =  "Salary Arrear paid for the month of "+self.from_month
		pb_je.posting_date = nowdate()               
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
				"business_activity": default_business_activity,
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
				"business_activity": default_business_activity,
				"credit_in_account_currency": flt(net_payable,2),
				"credit": flt(net_payable,2),
			})

		pb_je.flags.ignore_permissions = 1 
		pb_je.insert()
		#Salary Tax and HC Bank Entry End -----------------------------------------------
		self.db_set("journal_entries_created", 1)
		frappe.db.commit()
	##### Ver3.0.190304 Ends

@frappe.whitelist()
def arrear_payment_has_bank_entries(name):
	response = {}
	bank_entries = get_arrear_payment_bank_entries(name)
	response['submitted'] = 1 if bank_entries else 0

	return response

def get_arrear_payment_bank_entries(arrear_payment_name):
	journal_entries = frappe.db.sql(
		'select name from `tabJournal Entry Account` '
		'where reference_type="Salary Arrear Payment" '
		'and reference_name=%s and docstatus=1',
		arrear_payment_name,
		as_dict=1
	)

	return journal_entries
