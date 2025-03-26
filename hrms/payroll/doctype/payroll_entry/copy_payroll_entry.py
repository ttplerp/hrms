# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT, date_diff, get_last_day
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba
# from erpnext.accounts.doctype.hr_accounts_settings.hr_accounts_settings import get_bank_account

class PayrollEntry(Document):
	def onload(self):
		if not self.docstatus==1 or self.salary_slips_submitted:
				return

		# check if salary slips were manually submitted
		entries = frappe.db.count("Salary Slip", {'payroll_entry': self.name, 'docstatus': 1}, ['name'])
		if cint(entries) == len(self.employees):
				self.set_onload("submitted_ss", True)

	def validate(self):
		self.set_month_dates()

	def on_submit(self):
		# self.check_process_stats()
		self.submit_salary_slips()

	def before_submit(self):
		# ver.2020.10.20 Begins, following code is commented by SHIV on 2020/10/20
		'''
		if self.validate_attendance:
			if self.validate_employee_attendance():
				frappe.throw(_("Cannot Submit, Employees left to mark attendance"))
		'''
		# ver.2020.10.20 Ends
		pass

	def on_cancel(self):
		# ver.2020.10.21 Begins
		# following code commented by SHIV on 2020.10.21
		'''
		frappe.delete_doc("Salary Slip", frappe.db.sql_list("""select name from `tabSalary Slip`
			where payroll_entry=%s """, (self.name)))
		'''
		# following code added by SHIV on 2020.10.21
		self.remove_salary_slips()
		# ver.2020.10.21 Ends
		from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries

		unlink_ref_doc_from_payment_entries(self)
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
		pass

	def on_cancel_after_draft(self):
		self.remove_salary_slips()

	def check_process_stats(self):
		error_msg = ""
		for row in self.get("employees"):
			if row.error:
				error_msg += '<tr><td style="padding: 3px;"><b>{}</b><br>{}</td><td style="padding: 3px;">{}</td></tr>'.format(row.employee, row.employee_name, row.error)
		
		if error_msg:
			error_msg = '<table border="1px">{}</table>'.format(error_msg)
			frappe.throw(_("Salary slips for the following employees not created. <br>{}").format(error_msg), title="Failed")

	# ver.2020.10.20 Begins
	# following method copied from NRDCL by SHIV on 2020/10/20
	def get_emp_list(self, process_type=None):
		self.set_month_dates()

		cond = self.get_filter_condition()
		cond += self.get_joining_relieving_condition()
   
		emp_list = frappe.db.sql("""
			select t1.name as employee, t1.employee_name, t1.department, t1.designation
			from `tabEmployee` t1
			where not exists(select 1
					from `tabSalary Slip` as t3
					where t3.employee = t1.name
					and t3.docstatus != 2
					and t3.fiscal_year = '{}'
					and t3.month = '{}')
			and t1.status = 'Active'
			{}
			order by t1.branch, t1.name
		""".format(self.fiscal_year, self.month, cond), as_dict=True)

		if not emp_list:
			frappe.msgprint(_("No employees found for processing or Salary Slips already created"))
		return emp_list

	@frappe.whitelist()
	def fill_employee_details(self):
		self.set('employees', [])
		employees = self.get_emp_list()
		if not employees:
			frappe.throw(_("No employees for the mentioned criteria"))

		for d in employees:
			self.append('employees', d)

		self.number_of_employees = len(employees)
		return self.number_of_employees
		# ver.2020.10.20 Begins, following code is commented by SHIV on 2020/10/20
		'''
		if self.validate_attendance:
			return self.validate_employee_attendance()
		'''
		# ver.2020.10.20 Ends

	def get_filter_condition(self):
		self.check_mandatory()

		cond = ''
		
		# Following line is replaced by subsequent by SHIV on 2020/10/20, employee filter added
		#for f in ['company', 'branch', 'department', 'designation']:
		for f in ['company', 'branch', 'department', 'designation', 'employee']:
			if self.get(f):
				cond += " and t1." + f + " = '" + self.get(f).replace("'", "\'") + "'"

		return cond

	def get_joining_relieving_condition(self):
		cond = """
			and ifnull(t1.date_of_joining, '0000-00-00') <= '%(end_date)s'
			and ifnull(t1.relieving_date, '2199-12-31') >= '%(start_date)s'
		""" % {"start_date": self.start_date, "end_date": self.end_date}
		return cond

	# following method created by SHIV on 2020/10/20
	def set_month_dates(self):
		months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
		month = str(int(months.index(self.month_name))+1).rjust(2,"0")

		month_start_date = "-".join([str(self.fiscal_year), month, "01"])
		month_end_date   = get_last_day(month_start_date)

		self.start_date = month_start_date
		self.end_date = month_end_date
		self.month = month

	def check_mandatory(self):
		# following line is replaced by subsequent by SHIV on 2020/10/20
		#for fieldname in ['company', 'start_date', 'end_date']:
		for fieldname in ['company', 'fiscal_year', 'month']:
			if not self.get(fieldname):
				frappe.throw(_("Please set {0}").format(self.meta.get_label(fieldname)))

	@frappe.whitelist()
	def create_salary_slips(self):
		"""
			Creates salary slip for selected employees if already not created
		"""
		self.check_permission('write')
		self.created = 1
		emp_list = [d.employee for d in self.get_emp_list()]

		if emp_list:
			args = frappe._dict({
				"salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet,
				"payroll_frequency": self.payroll_frequency,
				"start_date": self.start_date,
				"end_date": self.end_date,
				"company": self.company,
				"posting_date": self.posting_date,
				"deduct_tax_for_unclaimed_employee_benefits": self.deduct_tax_for_unclaimed_employee_benefits,
				"deduct_tax_for_unsubmitted_tax_exemption_proof": self.deduct_tax_for_unsubmitted_tax_exemption_proof,
				"payroll_entry": self.name,
				"fiscal_year": self.fiscal_year,
				"month": self.month,
				"deduct_semso": self.deduct_semso,
				"semso_percent": self.semso_percent
			})
			if len(emp_list) > 300:
				frappe.enqueue(create_salary_slips_for_employees, timeout=600, employees=emp_list, args=args)
			else:
				create_salary_slips_for_employees(emp_list, args, publish_progress=False)
				# since this method is called via frm.call this doc needs to be updated manually
				self.reload()

	def get_sal_slip_list(self, ss_status, as_dict=False):
		"""
			Returns list of salary slips based on selected criteria
		"""
		cond = self.get_filter_condition()

		ss_list = frappe.db.sql("""
			select t1.name, t1.salary_structure from `tabSalary Slip` t1
			where t1.docstatus = %s and t1.start_date >= %s and t1.end_date <= %s
			and (t1.journal_entry is null or t1.journal_entry = "") and ifnull(salary_slip_based_on_timesheet,0) = %s %s
			and t1.payroll_entry = %s
		""" % ('%s', '%s', '%s','%s', cond, '%s'), (ss_status, self.start_date, self.end_date, self.salary_slip_based_on_timesheet, self.name), as_dict=as_dict)
		return ss_list

	def remove_salary_slips(self):
		self.check_permission('write')
		ss_list = self.get_sal_slip_list(ss_status=0)
		remove_salary_slips_for_employees(self, ss_list, publish_progress=False)

		if len(ss_list) > 300:
			remove_salary_slips_for_employees(self, ss_list, publish_progress=False)
		else:
			remove_salary_slips_for_employees(self, ss_list, publish_progress=False)

	def submit_salary_slips(self):
		self.check_permission('write')
		ss_list = self.get_sal_slip_list(ss_status=0)
		if len(ss_list) > 300:
			frappe.enqueue(submit_salary_slips_for_employees, timeout=600, payroll_entry=self, salary_slips=ss_list)
		else:
			submit_salary_slips_for_employees(self, ss_list, publish_progress=False)

	def email_salary_slip(self, submitted_ss):
		if frappe.db.get_single_value("Payroll Settings", "email_salary_slip_to_employee"):
			return
			for ss in submitted_ss:
				ss.email_salary_slip()

	def update_salary_slip_status(self, jv_name = None):
		ss_list = self.get_sal_slip_list(ss_status=1)
		for ss in ss_list:
			ss_obj = frappe.get_doc("Salary Slip",ss[0])
			frappe.db.set_value("Salary Slip", ss_obj.name, "journal_entry", jv_name)

	def set_start_end_dates(self):
		self.update(get_start_end_dates(self.payroll_frequency,
			self.start_date or self.posting_date, self.company))

	def get_cc_wise_entries(self, salary_component_pf):
		# Filters
		#cond = self.get_filter_condition()
		return frappe.db.sql("""
			select
				sd.institution_name,
				t1.cost_center             as cost_center,
				t1.business_activity       as business_activity,
				(case
					when sc.type = 'Earning' then sc.type
					else ifnull(sc.clubbed_component,sc.name)
				end)                       as salary_component,
				sc.type                    as component_type,
				(case
					when sc.type = 'Earning' then 0
					else ifnull(sc.is_remittable,0)
				end)                       as is_remittable,
				sc.gl_head                 as gl_head,
				sum(ifnull(t1.employer_pf,0)) as amount,
				(case
					when ifnull(sc.make_party_entry,0) = 1 then 'Payable'
					else 'Other'
				end) as account_type,
				(case
					when ifnull(sc.make_party_entry,0) = 1 then 'Employee'
					else 'Other'
				end) as party_type,
				(case
					when ifnull(sc.make_party_entry,0) = 1 then t1.employee
					else 'Other'
				end) as party
			 from
				`tabSalary Slip` t1,
				`tabSalary Detail` sd,
				`tabSalary Component` sc,
				`tabCompany` c
			where t1.fiscal_year = '{0}'
			  and t1.month       = '{1}'
			  and t1.docstatus   = 1
			  and sd.parent      = t1.name
			  and sd.salary_component = '{2}'
			  and sc.name        = sd.salary_component
			  and c.name         = t1.company
			  and t1.payroll_entry = '{3}'
			  and exists(select 1
						from `tabPayroll Employee Detail` ped
						where ped.parent = t1.payroll_entry
						and ped.employee = t1.employee)
			group by 
				t1.cost_center,
				(case when sc.type = 'Earning' then sc.type else ifnull(sc.clubbed_component,sc.name) end),
				sc.type,
				(case when sc.type = 'Earning' then 0 else ifnull(sc.is_remittable,0) end),
				sc.gl_head,
				(case when ifnull(sc.make_party_entry,0) = 1 then 'Payable' else 'Other' end),
				(case when ifnull(sc.make_party_entry,0) = 1 then 'Employee' else 'Other' end),
				(case when ifnull(sc.make_party_entry,0) = 1 then t1.employee else 'Other' end)
			order by t1.cost_center, t1.business_activity, sc.type, sc.name
		""".format(self.fiscal_year, self.month, salary_component_pf, self.name),as_dict=1)

	def generate_txt_file(self):
		# File path
		file_path = '/files/'+str(self.name)+".txt"
		actual_file_path = '/home/frappe/erp/sites/bdb.erp.bt/public/files/'+str(self.name)+".txt"

		# Append mode ('a') will append to the end of the file
		total_pay = 0
		with open(actual_file_path, 'w') as file:
			for emp in self.employees:
				if not frappe.db.get_value("Employee", emp.employee, "bank_ac_no"):
					frappe.throw("Please set Bank Account No. for Employee {} in Employee Master".format(emp.employee))
				net_pay = frappe.db.get_value("Salary Slip", emp.salary_slip, "net_pay")
				total_pay += flt(net_pay)
				for a in range(17-len(str(net_pay))):
					net_pay = " "+str(net_pay)
				file.write(str(frappe.db.get_value("Employee", emp.employee, "bank_ac_no"))+"     BTN0010     C"+str(net_pay)+"Salary / Remit for "+str(self.month_name)[0:3]+" "+str(self.fiscal_year)+"\n")
			for a in range(17-len(str(total_pay))):
				total_pay = " "+str(total_pay)
			file.write("0010200050011    BTN0010     D"+str(total_pay)+"Pay / Remit for "+str(self.month_name)[0:3]+" "+str(self.fiscal_year)+"\n")
		self.file = file_path


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

		company = frappe.db.get("Company", self.company)
		default_bank_account    = frappe.db.get_value("Branch", self.processing_branch,"expense_bank_account")
		# default_bank_account = get_bank_account(self.processing_branch)
		default_payable_account = company.get("salary_payable_account")
		company_cc              = company.get("company_cost_center")
		default_gpf_account     = company.get("employer_contribution_to_pf")
		default_business_activity = get_default_ba()
		salary_component_pf     = "PF"
		cbs_enabled = frappe.db.exists("Company",{"csb_enabled":1})

		if not default_bank_account:
			frappe.throw(_("Please set default <b>Expense Bank Account</b> for processing branch {}")\
				.format(frappe.get_desk_link("Branch", self.processing_branch)))
		elif not default_payable_account:
			frappe.throw(_("Please set default <b>Salary Payable Account</b> for the Company"))
		elif not company_cc:
			company_cc = frappe.db.get_value("Branch", self.processing_branch, "cost_center")
			if not company_cc:
				frappe.throw(_("Please set <b>Default Cost Center</b> for the Company"))
		elif not default_gpf_account:
			frappe.throw(_("Please set account for <b>Employer Contribution to PF</b> for the Company"))

		# Filters
		#cond = self.get_filter_condition()
		
		# Salary Details
		cc = frappe.db.sql("""
			select
				(case
					when sc.type = 'Deduction' and ifnull(sc.make_party_entry,0) = 0 and ifnull(sc.make_cc_entry,0) = 0 then c.company_cost_center
					else t1.cost_center
				end)                       as cost_center,
				(case
					when sc.type = 'Deduction' and ifnull(sc.make_party_entry,0) = 0 then '{3}'
					else t1.business_activity
				end)                      as business_activity,
				(case
					when sc.type = 'Earning' then sc.type
					else ifnull(sc.clubbed_component,sc.name)
				end)                       as salary_component,
				sc.type                    as component_type,
				sc.group_by_institution_name as group_by_institution_name,
				sd.institution_name,
				(case
					when sc.type = 'Earning' then 0
					else ifnull(sc.is_remittable,0)
				end)                       as is_remittable,
				sc.gl_head                 as gl_head,
				sum(ifnull(sd.amount,0))   as amount,
				sum(ifnull(t1.employer_pf,0))   as employer_pf,
				(case
					when ifnull(sc.make_party_entry,0) = 1 then 'Payable'
					else 'Other'
				end) as account_type,
				(case
					when ifnull(sc.make_party_entry,0) = 1 then 'Employee'
					else 'Other'
				end) as party_type,
				(case
					when ifnull(sc.make_party_entry,0) = 1 then t1.employee
					else 'Other'
				end) as party
			 from
				`tabSalary Slip` t1,
				`tabSalary Detail` sd,
				`tabSalary Component` sc,
				`tabCompany` c
			where t1.fiscal_year = '{0}'
			  and t1.month       = '{1}'
			  and t1.docstatus   = 1
			  and sd.parent      = t1.name
			  and sc.name        = sd.salary_component
			  and c.name         = t1.company
			  and t1.payroll_entry = '{2}'
			  and exists(select 1
						from `tabPayroll Employee Detail` ped
						where ped.parent = t1.payroll_entry
						and ped.employee = t1.employee)
			group by 
				(case
					when sc.type = 'Deduction' and ifnull(sc.make_party_entry,0) = 0 and ifnull(sc.make_cc_entry,0) = 0 then c.company_cost_center
					else t1.cost_center
				end),
				(case
					when sc.type = 'Deduction' and ifnull(sc.group_by_institution_name,0) = 1 then sd.institution_name
					else t1.cost_center
				end),
				(case
					when sc.type = 'Deduction' and ifnull(sc.make_party_entry,0) = 0 then '{3}'
					else t1.business_activity
				end),
				(case when sc.type = 'Earning' then sc.type else ifnull(sc.clubbed_component,sc.name) end),
				sc.type,
				(case when sc.type = 'Earning' then 0 else ifnull(sc.is_remittable,0) end),
				sc.gl_head,
				(case when ifnull(sc.make_party_entry,0) = 1 then 'Payable' else 'Other' end),
				(case when ifnull(sc.make_party_entry,0) = 1 then 'Employee' else 'Other' end),
				(case when ifnull(sc.make_party_entry,0) = 1 then t1.employee else 'Other' end)
			order by t1.cost_center, t1.business_activity, sc.type, sc.name
		""".format(self.fiscal_year, self.month, self.name, default_business_activity),as_dict=1)

		posting        = frappe._dict()
		cc_wise_totals = frappe._dict()
		tot_payable_amt= 0
		# frappe.throw(str(cc))
		for index, rec in enumerate(cc):
			# To Payables
			tot_payable_amt += (-1*flt(rec.amount) if rec.component_type == 'Deduction' else flt(rec.amount))
			posting.setdefault("to_payables",[]).append({
				"account"        : rec.gl_head,
				"credit_in_account_currency" if rec.component_type == 'Deduction' else "debit_in_account_currency": flt(rec.amount),
				"against_account": default_payable_account,
				"cost_center"    : rec.cost_center if rec.cost_center else company_cc,
				"business_activity" : rec.business_activity,
				"party_check"    : 0,
				"account_type"   : rec.account_type if rec.party_type == "Employee" else "",
				"party_type"     : rec.party_type if rec.party_type == "Employee" else "",
				"party"          : rec.party if rec.party_type == "Employee" else "",
				"party_check": 0,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"salary_component": rec.salary_component
			}) 
				
			# Remittance
			if rec.is_remittable and rec.component_type == 'Deduction':
				remit_amount    = 0
				remit_gl_list   = [rec.gl_head,default_gpf_account] if rec.salary_component == salary_component_pf else [rec.gl_head]
				# remit_gl_list = [rec.gl_head]
				for r in remit_gl_list:
					# remit_amount += flt(rec.amount)
					if r == default_gpf_account:
						# for i in self.get_cc_wise_entries(salary_component_pf):
						remit_amount += flt(rec.employer_pf)
						posting.setdefault(rec.salary_component,[]).append({
							"account"       : r,
							"debit_in_account_currency" : flt(rec.employer_pf),
							"cost_center"   : rec.cost_center if rec.cost_center else company_cc,
							"business_activity" : rec.business_activity,
							"party_check"   : 0,
							"account_type"   : rec.account_type if rec.party_type == "Employee" else "",
							"party_type"     : rec.party_type if rec.party_type == "Employee" else "",
							"party"          : rec.party if rec.party_type == "Employee" else "",
							"reference_type": self.doctype,
							"reference_name": self.name,
							"salary_component": rec.salary_component
						})
					else:
						remit_amount += flt(rec.amount)
						if rec.group_by_institution_name == 0:
							posting.setdefault(rec.salary_component,[]).append({
								"account"       : r,
								"debit_in_account_currency" : flt(rec.amount),
								"cost_center"   : rec.cost_center if rec.cost_center else company_cc,
								"business_activity" : rec.business_activity,
								"party_check"   : 0,
								"account_type"   : rec.account_type if rec.party_type == "Employee" else "",
								"party_type"     : rec.party_type if rec.party_type == "Employee" else "",
								"party"          : rec.party if rec.party_type == "Employee" else "",
								"reference_type": self.doctype,
								"reference_name": self.name,
								"salary_component": rec.salary_component
							})
						else:
							posting.setdefault(rec.salary_component,[]).append({
								"account"       : r,
								"debit_in_account_currency" : flt(rec.amount),
								"cost_center"   : rec.cost_center if rec.cost_center else company_cc,
								"business_activity" : rec.business_activity,
								"account_type"   : rec.account_type if rec.party_type == "Employee" else "",
								"party_type"     : "Supplier",
								"party"          : rec.institution_name,
								"party_check": 0,
								"reference_type": self.doctype,
								"reference_name": self.name,
								"salary_component": rec.salary_component
							})
				if not any("credit_in_account_currency" in d for d in posting[rec.salary_component]):
					posting.setdefault(rec.salary_component,[]).append({
						"account"       : default_bank_account,
						"credit_in_account_currency" : flt(remit_amount),
						"cost_center"   : rec.cost_center if rec.cost_center else company_cc,
						"business_activity" : rec.business_activity,
						"party_check"   : 0,
						"reference_type": self.doctype,
						"reference_name": self.name,
						"salary_component": rec.salary_component
					})
				else:
					# frappe.throw(str(posting[rec.salary_component][index]['debit_in_account_currency']))
					# frappe.msgprint(str(posting[rec.salary_component]))
					if "credit_in_account_currency" in posting[rec.salary_component][next(id for id,item in enumerate(posting[rec.salary_component]) if 'credit_in_account_currency' in item)]:
						# frappe.throw(str(posting[rec.salary_component][0]['debit_in_account_currency']))
						posting[rec.salary_component][next(id for id,item in enumerate(posting[rec.salary_component]) if 'credit_in_account_currency' in item)]['credit_in_account_currency'] += flt(remit_amount)
						# frappe.throw(str(posting[rec.salary_component][0]))
		# frappe.throw(str(len(posting['PF'])))

		# To Bank
		if posting.get("to_payables") and len(posting.get("to_payables")):
			posting.setdefault("to_bank",[]).append({
				"account"       : default_payable_account,
				"debit_in_account_currency": flt(tot_payable_amt),
				"cost_center"   : company_cc,
				"business_activity": default_business_activity,
				"party_check"   : 0,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"salary_component": rec.salary_component
			})
			posting.setdefault("to_bank",[]).append({
				"account"       : default_bank_account,
				"credit_in_account_currency": flt(tot_payable_amt),
				"cost_center"   : company_cc,
				"business_activity": default_business_activity,
				"party_check"   : 0,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"salary_component": rec.salary_component
			})
			posting.setdefault("to_payables",[]).append({
				"account"       : default_payable_account,
				"credit_in_account_currency" : flt(tot_payable_amt),
				"cost_center"   : company_cc,
				"business_activity": default_business_activity,
				"party_check"   : 0,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"salary_component": "Net Pay"
			})
		# if frappe.session.user == "Administrator":
		# frappe.throw(str(posting))
		# Final Posting to accounts
		if posting:
			jv_name, v_title = None, ""
			for i in posting:
				if i == "to_payables":
					v_title         = "To Payables" if not cbs_enabled else ""
					v_voucher_type  = "Journal Entry"
					v_naming_series = "Journal Voucher"
				else:
					if i == "to_bank":
						v_title = "To Bank"
						v_voucher_type  = "Bank Entry" if not cbs_enabled else "Journal Entry"
						v_naming_series = "Bank Payment Voucher" if not cbs_enabled else "Journal Voucher"
					else:
						v_title = i + " " + "Remittance"
						if cbs_enabled:
							v_voucher_type = "Journal Entry"
							v_naming_series = "Journal Voucher"
							if i == "Salary Tax":
								v_voucher_type = "Bank Entry"
								v_naming_series = "Bank Payment Voucher"
						else:
							v_voucher_type = "Bank Entry"
							v_naming_series = "Bank Payment Voucher"

				if v_title:
					v_title = "SALARY "+str(self.fiscal_year)+str(self.month)+" - "+str(v_title)
				else:
					v_title = "SALARY "+str(self.fiscal_year)+str(self.month)				
     
				doc = frappe.get_doc({
						"doctype": "Journal Entry",
						"voucher_type": v_voucher_type,
						"naming_series": v_naming_series,
						"title": v_title,
						"fiscal_year": self.fiscal_year,
						"remark": v_title,
						# "user_remark": "Salary ["+str(self.fiscal_year)+str(self.month)+"] - "+str(v_title),
						"posting_date": nowdate(),                     
						"company": self.company,
						"accounts": sorted(posting[i], key=lambda item: item['cost_center']),
						"branch": self.processing_branch,
						"reference_type": self.doctype,
						"reference_name": self.name,
					})
				doc.flags.ignore_permissions = 1 
				doc.insert()

				if i == "to_payables":
					#doc.submit() #Added by Thukten to submit Payable from HR
					jv_name = doc.name

			if jv_name:
				self.update_salary_slip_status(jv_name = jv_name)
			#self.generate_txt_file()	
			frappe.msgprint(_("Salary posting to accounts is successful."),title="Posting Successful")
		else:
			frappe.throw(_("No data found"),title="Posting failed")
	##### Ver3.0.190304 Ends


@frappe.whitelist()
def get_start_end_dates(payroll_frequency, start_date=None, company=None):
	'''Returns dict of start and end dates for given payroll frequency based on start_date'''

	if payroll_frequency == "Monthly" or payroll_frequency == "Bimonthly" or payroll_frequency == "":
		fiscal_year = get_fiscal_year(start_date, company=company)[0]
		month = "%02d" % getdate(start_date).month
		m = get_month_details(fiscal_year, month)
		if payroll_frequency == "Bimonthly":
			if getdate(start_date).day <= 15:
				start_date = m['month_start_date']
				end_date = m['month_mid_end_date']
			else:
				start_date = m['month_mid_start_date']
				end_date = m['month_end_date']
		else:
			start_date = m['month_start_date']
			end_date = m['month_end_date']

	if payroll_frequency == "Weekly":
		end_date = add_days(start_date, 6)

	if payroll_frequency == "Fortnightly":
		end_date = add_days(start_date, 13)

	if payroll_frequency == "Daily":
		end_date = start_date

	return frappe._dict({
		'start_date': start_date, 'end_date': end_date
	})

def get_frequency_kwargs(frequency_name):
	frequency_dict = {
		'monthly': {'months': 1},
		'fortnightly': {'days': 14},
		'weekly': {'days': 7},
		'daily': {'days': 1}
	}
	return frequency_dict.get(frequency_name)


@frappe.whitelist()
def get_end_date(start_date, frequency):
	start_date = getdate(start_date)
	frequency = frequency.lower() if frequency else 'monthly'
	kwargs = get_frequency_kwargs(frequency) if frequency != 'bimonthly' else get_frequency_kwargs('monthly')

	# weekly, fortnightly and daily intervals have fixed days so no problems
	end_date = add_to_date(start_date, **kwargs) - relativedelta(days=1)
	if frequency != 'bimonthly':
		return dict(end_date=end_date.strftime(DATE_FORMAT))

	else:
		return dict(end_date='')


def get_month_details(year, month):
	ysd = frappe.db.get_value("Fiscal Year", year, "year_start_date")
	if ysd:
		import calendar, datetime
		diff_mnt = cint(month)-cint(ysd.month)
		if diff_mnt<0:
			diff_mnt = 12-int(ysd.month)+cint(month)
		msd = ysd + relativedelta(months=diff_mnt) # month start date
		month_days = cint(calendar.monthrange(cint(msd.year) ,cint(month))[1]) # days in month
		mid_start = datetime.date(msd.year, cint(month), 16) # month mid start date
		mid_end = datetime.date(msd.year, cint(month), 15) # month mid end date
		med = datetime.date(msd.year, cint(month), month_days) # month end date
		return frappe._dict({
			'year': msd.year,
			'month_start_date': msd,
			'month_end_date': med,
			'month_mid_start_date': mid_start,
			'month_mid_end_date': mid_end,
			'month_days': month_days
		})
	else:
		frappe.throw(_("Fiscal Year {0} not found").format(year))

def get_payroll_entry_bank_entries(payroll_entry_name):
	journal_entries = frappe.db.sql(
		'select name from `tabJournal Entry Account` '
		'where reference_type="Payroll Entry" '
		'and reference_name=%s and docstatus=1',
		payroll_entry_name,
		as_dict=1
	)

	return journal_entries


@frappe.whitelist()
def payroll_entry_has_bank_entries(name):
	response = {}
	bank_entries = get_payroll_entry_bank_entries(name)
	response['submitted'] = 1 if bank_entries else 0

	return response

# ver.2020.10.20 Begins, by SHIV on 2020/10/20
def remove_salary_slips_for_employees(payroll_entry, salary_slips, publish_progress=True):
	deleted_ss = []
	not_deleted_ss = []
	frappe.flags.via_payroll_entry = True

	count = 0
	refresh_interval = 25
	total_count = len(salary_slips)
	for ss in salary_slips:
		try:
			frappe.delete_doc("Salary Slip", ss[0], for_reload=True)
			deleted_ss.append(ss[0])
		except frappe.ValidationError:
			not_deleted_ss.append(ss[0])

		count += 1
		if publish_progress:
			show_progress = 0
			if count <= refresh_interval:
				show_progress = 1
			elif refresh_interval > total_count:
				show_progress = 1
			elif count%refresh_interval == 0:
				show_progress = 1
			elif count > total_count-refresh_interval:
				show_progress = 1

			if show_progress:
				description = " Processing {}: ".format(ss[0]) + "["+str(count)+"/"+str(total_count)+"]"
				frappe.publish_progress(count*100/total_count, 
							title = _("Removing Salary Slips..."),
							description = description)
	if deleted_ss:
		frappe.msgprint(_("Salary Slips Removed Successfully"))

	if not deleted_ss and not not_deleted_ss:
		frappe.msgprint(_("No salary slip found to remove for the above selected criteria OR salary slip already submitted"))

	if not_deleted_ss:
		frappe.msgprint(_("Could not submit some Salary Slips"))
	payroll_entry.reload()

# following method is created by SHIV on 2020/10/20
def create_salary_slips_for_employees(employees, args, title=None, publish_progress=True):
	salary_slips_exists_for = get_existing_salary_slips(employees, args)
	count=0
	successful = 0
	failed = 0
	payroll_entry = frappe.get_doc("Payroll Entry", args.payroll_entry)

	payroll_entry.set('employees_failed', [])
	refresh_interval = 25
	total_count = len(set(employees))
	for emp in payroll_entry.get("employees"):
		if emp.employee in employees and emp.employee not in salary_slips_exists_for:
			error = None
			args.update({
				"doctype": "Salary Slip",
				"employee": emp.employee
			})

			try:
				ss = frappe.get_doc(args)
				ss.insert()
				successful += 1
			except Exception as e:
				error = str(e)
				failed += 1
			count+=1

			ped = frappe.get_doc("Payroll Employee Detail", emp.name)
			ped.db_set("salary_slip", ss.name)
			if error:
				ped.db_set("status", "Failed")
				ped.db_set("error", error)
				payroll_entry.append('employees_failed',{
					'employee': emp.employee,
					'employee_name': emp.employee_name,
					'status': 'Failed',
					'error': error
				})
			else:
				ped.db_set("status", "Success")
    
			if publish_progress:
				show_progress = 0
				if count <= refresh_interval:
					show_progress = 1
				elif refresh_interval > total_count:
					show_progress = 1
				elif count%refresh_interval == 0:
					show_progress = 1
				elif count > total_count-refresh_interval:
					show_progress = 1
				
				if show_progress:
					description = " Processing {}: ".format(ss.name if ss else emp.employee) + "["+str(count)+"/"+str(total_count)+"]"
					frappe.publish_progress(count*100/len(set(employees) - set(salary_slips_exists_for)),
						title = title if title else _("Creating Salary Slips..."),
						description = description)
					pass
	payroll_entry.db_set("salary_slips_created", 0 if failed else 1)
	payroll_entry.db_set("successful", cint(payroll_entry.successful)+cint(successful))
	payroll_entry.db_set("failed", cint(payroll_entry.number_of_employees)-(cint(payroll_entry.successful)))
	payroll_entry.reload()

def get_existing_salary_slips(employees, args):
	return frappe.db.sql_list("""
		select distinct employee from `tabSalary Slip`
		where docstatus!= 2 and company = %s
			and start_date >= %s and end_date <= %s
			and employee in (%s)
	""" % ('%s', '%s', '%s', ', '.join(['%s']*len(employees))),
		[args.company, args.start_date, args.end_date] + employees)

# ver.2020.10.21 Begins
# following code is created by SHIV on 2020/10/21
@frappe.whitelist()
def submit_salary_slips_for_employees(payroll_entry, salary_slips, publish_progress=True):
	submitted_ss = []
	not_submitted_ss = []
	frappe.flags.via_payroll_entry = True

	count = 0
	refresh_interval = 25
	total_count = len(salary_slips)
	for ss in salary_slips:
		ss_obj = frappe.get_doc("Salary Slip",ss[0])
		if ss_obj.net_pay<0:
			not_submitted_ss.append(ss[0])
		else:
			try:
				ss_obj.submit()
				submitted_ss.append(ss_obj)
			except frappe.ValidationError:
				not_submitted_ss.append(ss[0])

		count += 1
		if publish_progress:
			show_progress = 0
			if count <= refresh_interval:
				show_progress = 1
			elif refresh_interval > total_count:
				show_progress = 1
			elif count%refresh_interval == 0:
				show_progress = 1
			elif count > total_count-refresh_interval:
				show_progress = 1

			if show_progress:
				description = " Processing {}: ".format(ss[0]) + "["+str(count)+"/"+str(total_count)+"]"
				frappe.publish_progress(count*100/total_count, 
							title = _("Submitting Salary Slips..."),
							description = description)
	if submitted_ss:
		#payroll_entry.make_accrual_jv_entry()
		frappe.msgprint(_("Salary Slip submitted for period from {0} to {1}")
			.format(ss_obj.start_date, ss_obj.end_date))

		payroll_entry.email_salary_slip(submitted_ss)
		payroll_entry.db_set("salary_slips_submitted", 1)
		payroll_entry.reload()
		# payroll_entry.notify_update()

	if not submitted_ss and not not_submitted_ss:
		frappe.msgprint(_("No salary slip found to submit for the above selected criteria OR salary slip already submitted"))

	if not_submitted_ss:
		frappe.msgprint(_("Could not submit some Salary Slips"))

def get_payroll_entries_for_jv(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		select name from `tabPayroll Entry`
		where `{key}` LIKE %(txt)s
		and name not in
			(select reference_name from `tabJournal Entry Account`
				where reference_type="Payroll Entry")
		order by name limit %(start)s, %(page_len)s"""
		.format(key=searchfield), {
			'txt': "%%%s%%" % frappe.db.escape(txt),
			'start': start, 'page_len': page_len
		})

# CBS Integration
def get_emp_component_amount(payroll_entry, salary_component, party=None):
	if salary_component == "Net Pay":
		return frappe.db.sql("""select ss.employee, net_pay amount, "Net Pay" as salary_component,
					ss.bank_name, ss.bank_account_no account_number,
					0 as recovery_account,
					concat_ws(' ', ss.employee, ss.employee_name) remarks
				from `tabSalary Slip` ss
				where ss.payroll_entry = "{payroll_entry}"
				and ss.docstatus = 1
		""".format(payroll_entry=payroll_entry), as_dict=True)
	else:
		if not party:
			return frappe.db.sql("""select ss.employee, sum(sd.amount) amount, ss.branch, sd.salary_component,
						sd.institution_name bank_name, sd.reference_number account_number,
						1 as recovery_account,
						concat_ws(' ', ss.employee, ss.employee_name) remarks
					from `tabSalary Slip` ss, `tabSalary Detail` sd
					where ss.payroll_entry = "{payroll_entry}"
					and ss.docstatus = 1
					and sd.parent = ss.name
					and sd.salary_component = "{salary_component}"
			group by ss.employee""".format(payroll_entry=payroll_entry, salary_component=salary_component), as_dict=True)
		else:
			if salary_component != "Salary Advance Deductions":
				return frappe.db.sql("""select ss.employee, sum(sd.amount) amount, ss.branch, sd.salary_component,
							sd.institution_name bank_name, sd.reference_number account_number,
							1 as recovery_account,
							concat_ws(' ', ss.employee, ss.employee_name) remarks
						from `tabSalary Slip` ss, `tabSalary Detail` sd
						where ss.payroll_entry = "{payroll_entry}"
						and ss.docstatus = 1
						and sd.parent = ss.name
						and sd.salary_component = "{salary_component}"
						and ss.employee = "{employee}"
				group by ss.employee""".format(payroll_entry=payroll_entry, salary_component=salary_component, employee=party), as_dict=True)
			else:
				return frappe.db.sql("""select ss.employee, sum(sd.amount) amount, ss.branch, sd.salary_component,
							sd.institution_name bank_name, (select e.salary_advance_account from `tabEmployee` e where e.name = ss.employee) account_number,
							1 as recovery_account,
							concat_ws(' ', ss.employee, ss.employee_name) remarks
						from `tabSalary Slip` ss, `tabSalary Detail` sd
						where ss.payroll_entry = "{payroll_entry}"
						and ss.docstatus = 1
						and sd.parent = ss.name
						and sd.salary_component = "{salary_component}"
						and ss.employee = "{employee}"
				group by ss.employee""".format(payroll_entry=payroll_entry, salary_component=salary_component, employee=party), as_dict=True)

def get_gis_emp_details(payroll_entry, salary_component=None):
	return frappe.db.sql("""select '' as employee, sum(sd.amount) amount, ss.branch, sd.salary_component,
					sd.institution_name bank_name, (select case when a.gl_type = "CASA" then a.bank_account_no else a.account_number end from `tabAccount` a, `tabSalary Component` sc where sc.name = sd.salary_component and sc.gl_head = a.name) account_number,
					1 as recovery_account,
					sd.salary_component remarks
				from `tabSalary Slip` ss, `tabSalary Detail` sd
				where ss.payroll_entry = "{payroll_entry}"
				and ss.docstatus = 1
				and sd.parent = ss.name
				and sd.salary_component = "{salary_component}"
	""".format(payroll_entry=payroll_entry, salary_component=salary_component), as_dict=True)
def get_sws_emp_details(payroll_entry, salary_component=None):
	return frappe.db.sql("""select '' as employee, sum(sd.amount) amount, ss.branch, sd.salary_component,
					sd.institution_name bank_name, (select case when a.gl_type = "CASA" then a.bank_account_no else a.account_number end from `tabAccount` a, `tabSalary Component` sc where sc.name = sd.salary_component and sc.gl_head = a.name) account_number,
					1 as recovery_account,
					salary_component remarks
				from `tabSalary Slip` ss, `tabSalary Detail` sd
				where ss.payroll_entry = "{payroll_entry}"
				and ss.docstatus = 1
				and sd.parent = ss.name
				and sd.salary_component = "{salary_component}"
	""".format(payroll_entry=payroll_entry, salary_component=salary_component), as_dict=True)

def get_swl_emp_details(payroll_entry, salary_component=None):
	return frappe.db.sql("""select '' as employee, sum(sd.amount) amount, ss.branch, sd.salary_component,
					sd.institution_name bank_name, (select case when a.gl_type = "CASA" then a.bank_account_no else a.account_number end from `tabAccount` a, `tabSalary Component` sc where sc.name = sd.salary_component and sc.gl_head = a.name) account_number,
					1 as recovery_account,
					sd.salary_component remarks
				from `tabSalary Slip` ss, `tabSalary Detail` sd
				where ss.payroll_entry = "{payroll_entry}"
				and ss.docstatus = 1
				and sd.parent = ss.name
				and sd.salary_component = "{salary_component}"
	""".format(payroll_entry=payroll_entry, salary_component=salary_component), as_dict=True)

def get_hc_emp_details(payroll_entry, salary_component=None):
	return frappe.db.sql("""select ss.employee, sum(sd.amount) amount, ss.branch, sd.salary_component,
					sd.institution_name bank_name, (select case when a.gl_type = "CASA" then a.bank_account_no else a.account_number end from `tabAccount` a, `tabSalary Component` sc where sc.name = sd.salary_component and sc.gl_head = a.name) account_number,
					1 as recovery_account,
					sd.salary_component remarks
				from `tabSalary Slip` ss, `tabSalary Detail` sd
				where ss.payroll_entry = "{payroll_entry}"
				and ss.docstatus = 1
				and sd.parent = ss.name
				and sd.salary_component = "{salary_component}"
	""".format(payroll_entry=payroll_entry, salary_component=salary_component), as_dict=True)

def get_semso_emp_details(payroll_entry, salary_component=None):
	return frappe.db.sql("""select '' as employee, sum(sd.amount) amount, ss.branch, sd.salary_component,
					sd.institution_name bank_name, (select case when a.gl_type = "CASA" then a.bank_account_no else a.account_number end from `tabAccount` a, `tabSalary Component` sc where sc.name = sd.salary_component and sc.gl_head = a.name) account_number,
					1 as recovery_account,
					sd.salary_component remarks
				from `tabSalary Slip` ss, `tabSalary Detail` sd
				where ss.payroll_entry = "{payroll_entry}"
				and ss.docstatus = 1
				and sd.parent = ss.name
				and sd.salary_component = "{salary_component}"
	""".format(payroll_entry=payroll_entry, salary_component=salary_component), as_dict=True)
def get_loan_emp_details(payroll_entry, salary_component=None):
	return frappe.db.sql("""select '' as employee, sum(sd.amount) amount, ss.branch, sd.salary_component,
					sd.institution_name bank_name, (select case when a.gl_type = "CASA" then a.bank_account_no else a.account_number end from `tabAccount` a, `tabSalary Component` sc where sc.name = sd.salary_component and sc.gl_head = a.name) account_number,
					1 as recovery_account,
					sd.salary_component remarks
				from `tabSalary Slip` ss, `tabSalary Detail` sd
				where ss.payroll_entry = "{payroll_entry}"
				and ss.docstatus = 1
				and sd.parent = ss.name
				and sd.salary_component = "{salary_component}"
	""".format(payroll_entry=payroll_entry, salary_component = salary_component), as_dict=True)
def get_pf_emp_details(payroll_entry, salary_component=None):
	return frappe.db.sql("""select '' as employee, sum(sd.amount+ss.employer_pf) amount, ss.branch, sd.salary_component,
					sd.institution_name bank_name, (select case when a.gl_type = "CASA" then a.bank_account_no else a.account_number end from `tabAccount` a, `tabSalary Component` sc where sc.name = sd.salary_component and sc.gl_head = a.name) account_number,
					1 as recovery_account,
					sd.salary_component remarks
				from `tabSalary Slip` ss, `tabSalary Detail` sd
				where ss.payroll_entry = "{payroll_entry}"
				and ss.docstatus = 1
				and sd.parent = ss.name
				and sd.salary_component = "{salary_component}"
	""".format(payroll_entry=payroll_entry, salary_component = salary_component), as_dict=True)

def get_sss_emp_details(payroll_entry, salary_component=None):
	return frappe.db.sql("""select '' as employee, sum(sd.amount) amount, ss.branch, sd.salary_component,
					sd.institution_name bank_name, (select case when a.gl_type = "CASA" then a.bank_account_no else a.account_number end from `tabAccount` a, `tabSalary Component` sc where sc.name = sd.salary_component and sc.gl_head = a.name) account_number,
					1 as recovery_account,
					sd.salary_component remarks
				from `tabSalary Slip` ss, `tabSalary Detail` sd
				where ss.payroll_entry = "{payroll_entry}"
				and ss.docstatus = 1
				and sd.parent = ss.name
				and sd.salary_component = "{salary_component}"
	""".format(payroll_entry=payroll_entry, salary_component = salary_component), as_dict=True)
def get_tax_emp_details(payroll_entry, salary_component=None):
	return frappe.db.sql("""select '' as employee, sum(sd.amount) amount, ss.branch, sd.salary_component,
					sd.institution_name bank_name, (select case when a.gl_type = "CASA" then a.bank_account_no else a.account_number end from `tabAccount` a, `tabSalary Component` sc where sc.name = sd.salary_component and sc.gl_head = a.name) account_number,
					1 as recovery_account,
					sd.salary_component remarks
				from `tabSalary Slip` ss, `tabSalary Detail` sd
				where ss.payroll_entry = "{payroll_entry}"
				and ss.docstatus = 1
				and sd.parent = ss.name
				and sd.salary_component = "{salary_component}"
	""".format(payroll_entry=payroll_entry, salary_component = salary_component), as_dict=True)
