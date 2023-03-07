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
		
		# if self.validate_attendance:
		# 	if self.validate_employee_attendance():
		# 		frappe.throw(_("Cannot Submit, Employees left to mark attendance"))
		
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

		if self.department:
			cond += "and department = '{}'".format(self.department)
		if self.division:
			cond += "and division = '{}'".format(self.division)
		if self.section:
			cond += "and section = '{}'".format(self.section)
		if self.unit:
			cond += "and unit = '{}'".format(self.unit)

		emp_list = frappe.db.sql("""
			select t1.name as employee, t1.employee_name, t1.department, t1.designation
			from `tabEmployee` t1
			where not exists(select 1
					from `tabSalary Slip` as t3
					where t3.employee = t1.name
					and t3.docstatus != 2
					and t3.fiscal_year = '{}'
					and t3.month = '{}')
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
		
		if self.validate_attendance:
			return self.validate_employee_attendance()
		
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
				"month": self.month
			})
			if len(emp_list) > 300:
				# frappe.enqueue(create_salary_slips_for_employees, timeout=600, employees=emp_list, args=args)
				create_salary_slips_for_employees(emp_list, args, self.validate_attendance, publish_progress=True)
			else:
				create_salary_slips_for_employees(emp_list, args, self.validate_attendance, publish_progress=False)
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

	@frappe.whitelist()
	def validate_employee_attendance(self):
		employees_to_mark_attendance = []
		days_in_payroll, days_holiday, days_attendance_marked = 0, 0, 0
		for employee_detail in self.employees:
			# frappe.msgprint(str(employee_detail))
			employee_joining_date = frappe.db.get_value(
				"Employee", employee_detail.employee, "date_of_joining"
			)
			start_date = self.start_date
			if employee_joining_date > getdate(self.start_date):
				start_date = employee_joining_date
			days_holiday = self.get_count_holidays_of_employee(employee_detail.employee, start_date)
			days_attendance_marked = self.get_count_employee_attendance(
				employee_detail.employee, start_date
			)
			days_in_payroll = date_diff(self.end_date, start_date) + 1
			if days_in_payroll > days_holiday + days_attendance_marked:
				employees_to_mark_attendance.append(
					{"employee": employee_detail.employee, "employee_name": employee_detail.employee_name}
				)
		html = frappe.db.get_value("Print Format", "Employee Attendance", "html")
		#frappe.msgprint(str(employees_to_mark_attendance))
		return employees_to_mark_attendance, html

	# ver.2020.10.21 Begins, following code commented by SHIV on 2020.10.21
	'''

	def get_salary_component_account(self, salary_component):
		account = frappe.db.get_value("Salary Component Account",
			{"parent": salary_component, "company": self.company}, "default_account")

		if not account:
			frappe.throw(_("Please set default account in Salary Component {0}")
				.format(salary_component))

		return account

	def get_salary_components(self, component_type):
		salary_slips = self.get_sal_slip_list(ss_status = 1, as_dict = True)
		if salary_slips:
			salary_components = frappe.db.sql("""select salary_component, amount, parentfield
				from `tabSalary Detail` where parentfield = '%s' and parent in (%s)""" %
				(component_type, ', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=True)
			return salary_components

	def get_salary_component_total(self, component_type = None):
		salary_components = self.get_salary_components(component_type)
		if salary_components:
			component_dict = {}
			for item in salary_components:
				add_component_to_accrual_jv_entry = True
				if component_type == "earnings":
					is_flexible_benefit, only_tax_impact = frappe.db.get_value("Salary Component", item['salary_component'], ['is_flexible_benefit', 'only_tax_impact'])
					if is_flexible_benefit == 1 and only_tax_impact ==1:
						add_component_to_accrual_jv_entry = False
				if add_component_to_accrual_jv_entry:
					component_dict[item['salary_component']] = component_dict.get(item['salary_component'], 0) + item['amount']
			account_details = self.get_account(component_dict = component_dict)
			return account_details

	def get_account(self, component_dict = None):
		account_dict = {}
		for s, a in component_dict.items():
			account = self.get_salary_component_account(s)
			account_dict[account] = account_dict.get(account, 0) + a
		return account_dict

	def get_default_payroll_payable_account(self):
		payroll_payable_account = frappe.get_cached_value('Company',
			{"company_name": self.company},  "default_payroll_payable_account")

		if not payroll_payable_account:
			frappe.throw(_("Please set Default Payroll Payable Account in Company {0}")
				.format(self.company))

		return payroll_payable_account

	def make_accrual_jv_entry(self):
		self.check_permission('write')
		earnings = self.get_salary_component_total(component_type = "earnings") or {}
		deductions = self.get_salary_component_total(component_type = "deductions") or {}
		default_payroll_payable_account = self.get_default_payroll_payable_account()
		loan_details = self.get_loan_details()
		jv_name = ""
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		if earnings or deductions:
			journal_entry = frappe.new_doc('Journal Entry')
			journal_entry.voucher_type = 'Journal Entry'
			journal_entry.user_remark = _('Accrual Journal Entry for salaries from {0} to {1}')\
				.format(self.start_date, self.end_date)
			journal_entry.company = self.company
			journal_entry.posting_date = self.posting_date

			accounts = []
			payable_amount = 0

			# Earnings
			for acc, amount in earnings.items():
				payable_amount += flt(amount, precision)
				accounts.append({
						"account": acc,
						"debit_in_account_currency": flt(amount, precision),
						"party_type": '',
						"cost_center": self.cost_center,
						"project": self.project
					})

			# Deductions
			for acc, amount in deductions.items():
				payable_amount -= flt(amount, precision)
				accounts.append({
						"account": acc,
						"credit_in_account_currency": flt(amount, precision),
						"cost_center": self.cost_center,
						"party_type": '',
						"project": self.project
					})

			# Loan
			for data in loan_details:
				accounts.append({
						"account": data.loan_account,
						"credit_in_account_currency": data.principal_amount,
						"party_type": "Employee",
						"party": data.employee
					})

				if data.interest_amount and not data.interest_income_account:
					frappe.throw(_("Select interest income account in loan {0}").format(data.loan))

				if data.interest_income_account and data.interest_amount:
					accounts.append({
						"account": data.interest_income_account,
						"credit_in_account_currency": data.interest_amount,
						"cost_center": self.cost_center,
						"project": self.project,
						"party_type": "Employee",
						"party": data.employee
					})
				payable_amount -= flt(data.total_payment, precision)

			# Payable amount
			accounts.append({
				"account": default_payroll_payable_account,
				"credit_in_account_currency": flt(payable_amount, precision),
				"party_type": '',
			})

			journal_entry.set("accounts", accounts)
			journal_entry.title = default_payroll_payable_account
			journal_entry.save()

			try:
				journal_entry.submit()
				jv_name = journal_entry.name
				self.update_salary_slip_status(jv_name = jv_name)
			except Exception as e:
				frappe.msgprint(e)

		return jv_name
	'''
	# ver.2020.10.21 Ends

	# ver.2020.10.22 Begins, following code commented by SHIV on 2020/10/22
	'''
	def create_journal_entry(self, je_payment_amount, user_remark):
		default_payroll_payable_account = self.get_default_payroll_payable_account()
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.voucher_type = 'Bank Entry'
		journal_entry.user_remark = _('Payment of {0} from {1} to {2}')\
			.format(user_remark, self.start_date, self.end_date)
		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date

		payment_amount = flt(je_payment_amount, precision)

		journal_entry.set("accounts", [
			{
				"account": self.payment_account,
				"bank_account": self.bank_account,
				"credit_in_account_currency": payment_amount
			},
			{
				"account": default_payroll_payable_account,
				"debit_in_account_currency": payment_amount,
				"reference_type": self.doctype,
				"reference_name": self.name
			}
		])
		journal_entry.save(ignore_permissions = True)
	'''
	# ver.2020.10.22 Ends

	def update_salary_slip_status(self, jv_name = None):
		ss_list = self.get_sal_slip_list(ss_status=1)
		for ss in ss_list:
			ss_obj = frappe.get_doc("Salary Slip",ss[0])
			frappe.db.set_value("Salary Slip", ss_obj.name, "journal_entry", jv_name)

	def set_start_end_dates(self):
		self.update(get_start_end_dates(self.payroll_frequency,
			self.start_date or self.posting_date, self.company))

	def get_count_holidays_of_employee(self, employee, start_date):
		holiday_list = get_holiday_list_for_employee(employee)
		holidays = 0
		if holiday_list:
			days = frappe.db.sql(
				"""select count(*) from tabHoliday where
				parent=%s and holiday_date between %s and %s""",
				(holiday_list, start_date, self.end_date),
			)
			if days and days[0][0]:
				holidays = days[0][0]
		return holidays

	def get_count_employee_attendance(self, employee, start_date):
		marked_days = 0
		attendances = frappe.get_all(
			"Attendance",
			fields=["count(*)"],
			filters={"employee": employee, "attendance_date": ("between", [start_date, self.end_date])},
			as_list=1,
		)
		if attendances and attendances[0][0]:
			marked_days = attendances[0][0]
		return marked_days

	def get_cc_wise_entries(self, salary_component_pf):
		# Filters
		#cond = self.get_filter_condition()
		
		return frappe.db.sql("""
			select
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
				sca.account                 as gl_head,
				sum(ifnull(sd.amount,0))   as amount,
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
				`tabSalary Component Account` sca,
				`tabCompany` c
			where t1.fiscal_year = '{0}'
			  and t1.month       = '{1}'
			  and t1.docstatus   = 1
			  and sd.parent      = t1.name
			  and sd.salary_component = '{2}'
			  and sca.parent = sc.name
			  and sca.company = t1.company
			  and sc.name        = sd.salary_component
			  and c.name         = t1.company
			  and t1.payroll_entry = '{3}'
			  and exists(select 1
						from `tabPayroll Employee Detail` ped
						where ped.parent = t1.payroll_entry
						and ped.employee = t1.employee)
			group by 
				t1.cost_center,
				t1.company,
				(case when sc.type = 'Earning' then sc.type else ifnull(sc.clubbed_component,sc.name) end),
				sc.type,
				(case when sc.type = 'Earning' then 0 else ifnull(sc.is_remittable,0) end),
				sca.account,
				sca.company,
				(case when ifnull(sc.make_party_entry,0) = 1 then 'Payable' else 'Other' end),
				(case when ifnull(sc.make_party_entry,0) = 1 then 'Employee' else 'Other' end),
				(case when ifnull(sc.make_party_entry,0) = 1 then t1.employee else 'Other' end)
			order by t1.cost_center, t1.business_activity, sc.type, sc.name
		""".format(self.fiscal_year, self.month, salary_component_pf, self.name),as_dict=1)
	
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

		if not default_bank_account:
			frappe.throw(_("Please set default <b>Expense Bank Account</b> for processing branch {}")\
				.format(frappe.get_desk_link("Branch", self.processing_branch)))
		elif not default_payable_account:
			frappe.throw(_("Please set default <b>Salary Payable Account</b> for the Company"))
		elif not company_cc:
			frappe.throw(_("Please set <b>Default Cost Center</b> for the Company"))
		elif not default_gpf_account:
			frappe.throw(_("Please set account for <b>Employer Contribution to PF</b> for the Company"))

		# Filters
		#cond = self.get_filter_condition()
		
		# Salary Details
		cc = frappe.db.sql("""
			select
				(case
					when sc.type = 'Deduction' and ifnull(sc.make_party_entry,0) = 0 then c.company_cost_center
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
				(case
					when sc.type = 'Earning' then 0
					else ifnull(sc.is_remittable,0)
				end)                       as is_remittable,
				sca.account                 as gl_head,
				sum(ifnull(sd.amount,0))   as amount,
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
				`tabSalary Component Account` sca,
				`tabCompany` c
			where t1.fiscal_year = '{0}'
			  and t1.month       = '{1}'
			  and t1.docstatus   = 1
			  and sd.parent      = t1.name
			  and sc.name        = sd.salary_component
			  and sca.parent	 = sc.name
			  and c.name         = t1.company
			  and sca.company	 = t1.company
			  and t1.payroll_entry = '{2}'
			  and exists(select 1
						from `tabPayroll Employee Detail` ped
						where ped.parent = t1.payroll_entry
						and ped.employee = t1.employee)
			group by 
				(case
					when sc.type = 'Deduction' and ifnull(sc.make_party_entry,0) = 0 then c.company_cost_center
					else t1.cost_center
				end),
				(case
					when sc.type = 'Deduction' and ifnull(sc.make_party_entry,0) = 0 then '{3}'
					else t1.business_activity
				end),
				(case when sc.type = 'Earning' then sc.type else ifnull(sc.clubbed_component,sc.name) end),
				sc.type,
				(case when sc.type = 'Earning' then 0 else ifnull(sc.is_remittable,0) end),
				sca.account,
				sca.company,
				(case when ifnull(sc.make_party_entry,0) = 1 then 'Payable' else 'Other' end),
				(case when ifnull(sc.make_party_entry,0) = 1 then 'Employee' else 'Other' end),
				(case when ifnull(sc.make_party_entry,0) = 1 then t1.employee else 'Other' end)
			order by t1.cost_center, t1.business_activity, sc.type, sc.name
		""".format(self.fiscal_year, self.month, self.name, default_business_activity),as_dict=1)

		posting        = frappe._dict()
		cc_wise_totals = frappe._dict()
		tot_payable_amt= 0
		for rec in cc:
			# To Payables
			tot_payable_amt += (-1*flt(rec.amount) if rec.component_type == 'Deduction' else flt(rec.amount))
			posting.setdefault("to_payables",[]).append({
				"account"        : rec.gl_head,
				"credit_in_account_currency" if rec.component_type == 'Deduction' else "debit_in_account_currency": flt(rec.amount,2),
				"against_account": default_payable_account,
				"cost_center"    : rec.cost_center,
				"business_activity" : rec.business_activity,
				"party_check"    : 0,
				"account_type"   : rec.account_type if rec.party_type == "Employee" else "",
				"party_type"     : rec.party_type if rec.party_type == "Employee" else "",
				"party"          : rec.party if rec.party_type == "Employee" else "",
				"reference_type": self.doctype,
				"reference_name": self.name,
				"salary_component": rec.salary_component
			}) 
				
			# Remittance
			if rec.is_remittable and rec.component_type == 'Deduction':
				remit_amount    = 0
				remit_gl_list   = [rec.gl_head,default_gpf_account] if rec.salary_component == salary_component_pf else [rec.gl_head]

				for r in remit_gl_list:
					remit_amount += flt(rec.amount,2)
					if r == default_gpf_account:
						for i in self.get_cc_wise_entries(salary_component_pf):
							  posting.setdefault(rec.salary_component,[]).append({
								"account"       : r,
								"debit_in_account_currency" : flt(i.amount,2),
								"cost_center"   : i.cost_center,
								"business_activity" : i.business_activity,
								"party_check"   : 0,
								"account_type"   : i.account_type if i.party_type == "Employee" else "",
								"party_type"     : i.party_type if i.party_type == "Employee" else "",
								"party"          : i.party if i.party_type == "Employee" else "",
								"reference_type": self.doctype,
								"reference_name": self.name,
								"salary_component": rec.salary_component
							})
					else:
						posting.setdefault(rec.salary_component,[]).append({
							"account"       : r,
							"debit_in_account_currency" : flt(rec.amount,2),
							"cost_center"   : rec.cost_center,
							"business_activity" : rec.business_activity,
							"party_check"   : 0,
							"account_type"   : rec.account_type if rec.party_type == "Employee" else "",
							"party_type"     : rec.party_type if rec.party_type == "Employee" else "",
							"party"          : rec.party if rec.party_type == "Employee" else "",
							"reference_type": self.doctype,
							"reference_name": self.name,
							"salary_component": rec.salary_component
						})
					
				posting.setdefault(rec.salary_component,[]).append({
					"account"       : default_bank_account,
					"credit_in_account_currency" : flt(remit_amount,2),
					"cost_center"   : rec.cost_center,
					"business_activity" : rec.business_activity,
					"party_check"   : 0,
					"reference_type": self.doctype,
					"reference_name": self.name,
					"salary_component": rec.salary_component
				})

		# To Bank
		if posting.get("to_payables") and len(posting.get("to_payables")):
			posting.setdefault("to_bank",[]).append({
				"account"       : default_payable_account,
				"debit_in_account_currency": flt(tot_payable_amt,2),
				"cost_center"   : company_cc,
				"business_activity": default_business_activity,
				"party_check"   : 0,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"salary_component": rec.salary_component
			})
			posting.setdefault("to_bank",[]).append({
				"account"       : default_bank_account,
				"credit_in_account_currency": flt(tot_payable_amt,2),
				"cost_center"   : company_cc,
				"business_activity": default_business_activity,
				"party_check"   : 0,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"salary_component": rec.salary_component
			})
			posting.setdefault("to_payables",[]).append({
				"account"       : default_payable_account,
				"credit_in_account_currency" : flt(tot_payable_amt,2),
				"cost_center"   : company_cc,
				"business_activity": default_business_activity,
				"party_check"   : 0,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"salary_component": "Net Pay"
			})
		# if frappe.session.user == "Administrator":
		# 	frappe.throw("posting: "+str(posting))
		# Final Posting to accounts
		if posting:
			jv_name, v_title = None, ""
			for i in posting:
				if i == "to_payables":
					v_title         = "To Payables"
					v_voucher_type  = "Journal Entry"
					v_naming_series = "Journal Voucher"
				else:
					#v_title         = "To Bank" if i == "to_bank" else i
					v_title         = "To Cash" if i == "to_bank" else i
					v_voucher_type  = self.jv_entry_type
					v_naming_series = "Bank Payment Voucher" if self.jv_entry_type == "Bank Entry" else "Cash Payment Entry"

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
					doc.submit() #Added by Thukten to submit Payable from HR
					jv_name = doc.name

			if jv_name:
				self.update_salary_slip_status(jv_name = jv_name)		
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
@frappe.whitelist()
def create_salary_slips_for_employees(employees, args, validate_attendance, title=None, publish_progress=True):
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

			# try:
			ss = frappe.get_doc(args)
			ss.insert()
			successful += 1
			# except Exception as e:
				# frappe.throw(_("{}").format(e))
				# error = str(e)
				# failed += 1
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
	# payroll_entry.notify_update()
	# payroll_entry.salary_slips_created = 0 if failed else 1
	# payroll_entry.successful = cint(payroll_entry.successful)+cint(successful)
	# payroll_entry.failed = cint(payroll_entry.number_of_employees)-cint(payroll_entry.successful)
	# payroll_entry.save(ignore_permissions=True)
	# payroll_entry.reload()

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

# CBS Integration, following method created by SHIV on 2021/09/15
def get_emp_component_amount(payroll_entry, salary_component):
	if salary_component == "Net Pay":
		return frappe.db.sql("""select ss.employee, net_pay amount,
					ss.bank_name, ss.bank_account_no account_number,
					0 as recovery_account,
					concat_ws(' ', ss.employee, ss.employee_name) remarks
				from `tabSalary Slip` ss
				where ss.payroll_entry = "{payroll_entry}"
				and ss.docstatus = 1
		""".format(payroll_entry=payroll_entry), as_dict=True)
	else:
		return frappe.db.sql("""select ss.employee, sum(sd.amount) amount,
					sd.institution_name bank_name, sd.reference_number account_number,
					1 as recovery_account,
					concat_ws(' ', ss.employee, ss.employee_name) remarks
				from `tabSalary Slip` ss, `tabSalary Detail` sd
				where ss.payroll_entry = "{payroll_entry}"
				and ss.docstatus = 1
				and sd.parent = ss.name
				and sd.salary_component = "{salary_component}"
		group by ss.employee""".format(payroll_entry=payroll_entry, salary_component=salary_component), as_dict=True)



































# import json

# from dateutil.relativedelta import relativedelta

# import frappe
# from frappe import _
# from frappe.desk.reportview import get_filters_cond, get_match_cond
# from frappe.model.document import Document
# from frappe.query_builder.functions import Coalesce
# from frappe.utils import (
# 	DATE_FORMAT,
# 	add_days,
# 	add_to_date,
# 	cint,
# 	comma_and,
# 	date_diff,
# 	flt,
# 	get_link_to_form,
# 	getdate,
# )

# import erpnext
# from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
# 	get_accounting_dimensions,
# )
# from erpnext.accounts.utils import get_fiscal_year
# from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee


# class PayrollEntry(Document):
# 	def onload(self):
# 		if not self.docstatus == 1 or self.salary_slips_submitted:
# 			return

# 		# check if salary slips were manually submitted
# 		entries = frappe.db.count("Salary Slip", {"payroll_entry": self.name, "docstatus": 1}, ["name"])
# 		if cint(entries) == len(self.employees):
# 			self.set_onload("submitted_ss", True)

# 	def validate(self):
# 		self.number_of_employees = len(self.employees)
# 		self.set_status()

# 	def on_submit(self):
# 		self.set_status(update=True, status="Submitted")
# 		self.create_salary_slips()



# 	def set_status(self, status=None, update=False):
# 		if not status:
# 			status = {0: "Draft", 1: "Submitted", 2: "Cancelled"}[self.docstatus or 0]

# 		if update:
# 			self.db_set("status", status)
# 		else:
# 			self.status = status

# 	def validate_employee_details(self):
# 		emp_with_sal_slip = []
# 		for employee_details in self.employees:
# 			if frappe.db.exists(
# 				"Salary Slip",
# 				{
# 					"employee": employee_details.employee,
# 					"start_date": self.start_date,
# 					"end_date": self.end_date,
# 					"docstatus": 1,
# 				},
# 			):
# 				emp_with_sal_slip.append(employee_details.employee)

# 		if len(emp_with_sal_slip):
# 			frappe.throw(_("Salary Slip already exists for {0}").format(comma_and(emp_with_sal_slip)))

# 	def validate_payroll_payable_account(self):
# 		if frappe.db.get_value("Account", self.payroll_payable_account, "account_type"):
# 			frappe.throw(
# 				_(
# 					"Account type cannot be set for payroll payable account {0}, please remove and try again"
# 				).format(frappe.bold(get_link_to_form("Account", self.payroll_payable_account)))
# 			)

# 	def on_cancel(self):
# 		frappe.delete_doc(
# 			"Salary Slip",
# 			frappe.db.sql_list(
# 				"""select name from `tabSalary Slip`
# 			where payroll_entry=%s """,
# 				(self.name),
# 			),
# 		)
# 		self.db_set("salary_slips_created", 0)
# 		self.db_set("salary_slips_submitted", 0)
# 		self.set_status(update=True, status="Cancelled")
# 		self.db_set("error_message", "")

# 	def get_emp_list(self):
# 		"""
# 		Returns list of active employees based on selected criteria
# 		and for which salary structure exists
# 		"""
# 		self.check_mandatory()
# 		filters = self.make_filters()
# 		cond = get_filter_condition(filters)
# 		cond += get_joining_relieving_condition(self.start_date, self.end_date)

# 		condition = ""
# 		if self.payroll_frequency:
# 			condition = """and payroll_frequency = '%(payroll_frequency)s'""" % {
# 				"payroll_frequency": self.payroll_frequency
# 			}

# 		sal_struct = get_sal_struct(
# 			self.company, self.currency, self.salary_slip_based_on_timesheet, condition
# 		)
# 		if sal_struct:
# 			cond += "and t2.salary_structure IN %(sal_struct)s "
# 			cond += "and t2.payroll_payable_account = %(payroll_payable_account)s "
# 			cond += "and %(from_date)s >= t2.from_date"
# 			emp_list = get_emp_list(sal_struct, cond, self.end_date, self.payroll_payable_account)
# 			emp_list = remove_payrolled_employees(emp_list, self.start_date, self.end_date)
# 			return emp_list

# 	def make_filters(self):
# 		filters = frappe._dict()
# 		filters["company"] = self.company
# 		filters["branch"] = self.branch
# 		filters["department"] = self.department
# 		filters["designation"] = self.designation

# 		return filters

# 	@frappe.whitelist()
# 	def fill_employee_details(self):
# 		self.set("employees", [])
# 		employees = self.get_emp_list()
# 		if not employees:
# 			error_msg = _(
# 				"No employees found for the mentioned criteria:<br>Company: {0}<br> Currency: {1}<br>Payroll Payable Account: {2}"
# 			).format(
# 				frappe.bold(self.company),
# 				frappe.bold(self.currency),
# 				frappe.bold(self.payroll_payable_account),
# 			)
# 			if self.branch:
# 				error_msg += "<br>" + _("Branch: {0}").format(frappe.bold(self.branch))
# 			if self.department:
# 				error_msg += "<br>" + _("Department: {0}").format(frappe.bold(self.department))
# 			if self.designation:
# 				error_msg += "<br>" + _("Designation: {0}").format(frappe.bold(self.designation))
# 			if self.start_date:
# 				error_msg += "<br>" + _("Start date: {0}").format(frappe.bold(self.start_date))
# 			if self.end_date:
# 				error_msg += "<br>" + _("End date: {0}").format(frappe.bold(self.end_date))
# 			frappe.throw(error_msg, title=_("No employees found"))

# 		for d in employees:
# 			self.append("employees", d)



# 	def check_mandatory(self):
# 		for fieldname in ["company", "start_date", "end_date"]:
# 			if not self.get(fieldname):
# 				frappe.throw(_("Please set {0}").format(self.meta.get_label(fieldname)))

# 	@frappe.whitelist()
# 	def create_salary_slips(self):
# 		"""
# 		Creates salary slip for selected employees if already not created
# 		"""
# 		self.check_permission("write")
# 		employees = [emp.employee for emp in self.employees]
# 		if employees:
# 			args = frappe._dict(
# 				{
# 					"salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet,
# 					"payroll_frequency": self.payroll_frequency,
# 					"start_date": self.start_date,
# 					"end_date": self.end_date,
# 					"company": self.company,
# 					"posting_date": self.posting_date,
# 					"deduct_tax_for_unclaimed_employee_benefits": self.deduct_tax_for_unclaimed_employee_benefits,
# 					"deduct_tax_for_unsubmitted_tax_exemption_proof": self.deduct_tax_for_unsubmitted_tax_exemption_proof,
# 					"payroll_entry": self.name,
# 					"exchange_rate": self.exchange_rate,
# 					"currency": self.currency,
# 				}
# 			)
# 			if len(employees) > 30 or frappe.flags.enqueue_payroll_entry:
# 				self.db_set("status", "Queued")
# 				frappe.enqueue(
# 					create_salary_slips_for_employees,
# 					timeout=600,
# 					employees=employees,
# 					args=args,
# 					publish_progress=False,
# 				)
# 				frappe.msgprint(
# 					_("Salary Slip creation is queued. It may take a few minutes"),
# 					alert=True,
# 					indicator="blue",
# 				)
# 			else:
# 				create_salary_slips_for_employees(employees, args, publish_progress=False)
# 				# since this method is called via frm.call this doc needs to be updated manually
# 				self.reload()

# 	def get_sal_slip_list(self, ss_status, as_dict=False):
# 		"""
# 		Returns list of salary slips based on selected criteria
# 		"""

# 		ss = frappe.qb.DocType("Salary Slip")
# 		ss_list = (
# 			frappe.qb.from_(ss)
# 			.select(ss.name, ss.salary_structure)
# 			.where(
# 				(ss.docstatus == ss_status)
# 				& (ss.start_date >= self.start_date)
# 				& (ss.end_date <= self.end_date)
# 				& (ss.payroll_entry == self.name)
# 				& ((ss.journal_entry.isnull()) | (ss.journal_entry == ""))
# 				& (Coalesce(ss.salary_slip_based_on_timesheet, 0) == self.salary_slip_based_on_timesheet)
# 			)
# 		).run(as_dict=as_dict)

# 		return ss_list

# 	@frappe.whitelist()
# 	def submit_salary_slips(self):
# 		self.check_permission("write")
# 		salary_slips = self.get_sal_slip_list(ss_status=0)
# 		if len(salary_slips) > 30 or frappe.flags.enqueue_payroll_entry:
# 			self.db_set("status", "Queued")
# 			frappe.enqueue(
# 				submit_salary_slips_for_employees,
# 				timeout=600,
# 				payroll_entry=self,
# 				salary_slips=salary_slips,
# 				publish_progress=False,
# 			)
# 			frappe.msgprint(
# 				_("Salary Slip submission is queued. It may take a few minutes"),
# 				alert=True,
# 				indicator="blue",
# 			)
# 		else:
# 			submit_salary_slips_for_employees(self, salary_slips, publish_progress=False)

# 	def email_salary_slip(self, submitted_ss):
# 		if frappe.db.get_single_value("Payroll Settings", "email_salary_slip_to_employee"):
# 			for ss in submitted_ss:
# 				ss.email_salary_slip()

# 	def get_salary_component_account(self, salary_component):
# 		account = frappe.db.get_value(
# 			"Salary Component Account", {"parent": salary_component, "company": self.company}, "account"
# 		)

# 		if not account:
# 			frappe.throw(
# 				_("Please set account in Salary Component {0}").format(
# 					get_link_to_form("Salary Component", salary_component)
# 				)
# 			)

# 		return account

# 	def get_salary_components(self, component_type):
# 		salary_slips = self.get_sal_slip_list(ss_status=1, as_dict=True)

# 		if salary_slips:
# 			ss = frappe.qb.DocType("Salary Slip")
# 			ssd = frappe.qb.DocType("Salary Detail")
# 			salary_components = (
# 				frappe.qb.from_(ss)
# 				.join(ssd)
# 				.on(ss.name == ssd.parent)
# 				.select(ssd.salary_component, ssd.amount, ssd.parentfield, ss.salary_structure, ss.employee)
# 				.where(
# 					(ssd.parentfield == component_type) & (ss.name.isin(tuple([d.name for d in salary_slips])))
# 				)
# 			).run(as_dict=True)

# 			return salary_components

# 	def get_salary_component_total(self, component_type=None):
# 		salary_components = self.get_salary_components(component_type)
# 		if salary_components:
# 			component_dict = {}
# 			self.employee_cost_centers = {}
# 			for item in salary_components:
# 				employee_cost_centers = self.get_payroll_cost_centers_for_employee(
# 					item.employee, item.salary_structure
# 				)

# 				add_component_to_accrual_jv_entry = True
# 				if component_type == "earnings":
# 					is_flexible_benefit, only_tax_impact = frappe.get_cached_value(
# 						"Salary Component", item["salary_component"], ["is_flexible_benefit", "only_tax_impact"]
# 					)
# 					if is_flexible_benefit == 1 and only_tax_impact == 1:
# 						add_component_to_accrual_jv_entry = False

# 				if add_component_to_accrual_jv_entry:
# 					for cost_center, percentage in employee_cost_centers.items():
# 						amount_against_cost_center = flt(item.amount) * percentage / 100
# 						component_dict[(item.salary_component, cost_center)] = (
# 							component_dict.get((item.salary_component, cost_center), 0) + amount_against_cost_center
# 						)

# 			account_details = self.get_account(component_dict=component_dict)
# 			return account_details

# 	def get_payroll_cost_centers_for_employee(self, employee, salary_structure):
# 		if not self.employee_cost_centers.get(employee):
# 			ss_assignment_name = frappe.db.get_value(
# 				"Salary Structure Assignment",
# 				{"employee": employee, "salary_structure": salary_structure, "docstatus": 1},
# 				"name",
# 			)

# 			if ss_assignment_name:
# 				cost_centers = dict(
# 					frappe.get_all(
# 						"Employee Cost Center",
# 						{"parent": ss_assignment_name},
# 						["cost_center", "percentage"],
# 						as_list=1,
# 					)
# 				)
# 				if not cost_centers:
# 					default_cost_center, department = frappe.get_cached_value(
# 						"Employee", employee, ["payroll_cost_center", "department"]
# 					)
# 					if not default_cost_center and department:
# 						default_cost_center = frappe.get_cached_value(
# 							"Department", department, "payroll_cost_center"
# 						)
# 					if not default_cost_center:
# 						default_cost_center = self.cost_center

# 					cost_centers = {default_cost_center: 100}

# 				self.employee_cost_centers.setdefault(employee, cost_centers)

# 		return self.employee_cost_centers.get(employee, {})

# 	def get_account(self, component_dict=None):
# 		account_dict = {}
# 		for key, amount in component_dict.items():
# 			account = self.get_salary_component_account(key[0])
# 			account_dict[(account, key[1])] = account_dict.get((account, key[1]), 0) + amount
# 		return account_dict

# 	def make_accrual_jv_entry(self):
# 		self.check_permission("write")
# 		earnings = self.get_salary_component_total(component_type="earnings") or {}
# 		deductions = self.get_salary_component_total(component_type="deductions") or {}
# 		payroll_payable_account = self.payroll_payable_account
# 		jv_name = ""
# 		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

# 		if earnings or deductions:
# 			journal_entry = frappe.new_doc("Journal Entry")
# 			journal_entry.voucher_type = "Journal Entry"
# 			journal_entry.user_remark = _("Accrual Journal Entry for salaries from {0} to {1}").format(
# 				self.start_date, self.end_date
# 			)
# 			journal_entry.company = self.company
# 			journal_entry.posting_date = self.posting_date
# 			accounting_dimensions = get_accounting_dimensions() or []

# 			accounts = []
# 			currencies = []
# 			payable_amount = 0
# 			multi_currency = 0
# 			company_currency = erpnext.get_company_currency(self.company)

# 			# Earnings
# 			for acc_cc, amount in earnings.items():
# 				exchange_rate, amt = self.get_amount_and_exchange_rate_for_journal_entry(
# 					acc_cc[0], amount, company_currency, currencies
# 				)
# 				payable_amount += flt(amount, precision)
# 				accounts.append(
# 					self.update_accounting_dimensions(
# 						{
# 							"account": acc_cc[0],
# 							"debit_in_account_currency": flt(amt, precision),
# 							"exchange_rate": flt(exchange_rate),
# 							"cost_center": acc_cc[1] or self.cost_center,
# 							"project": self.project,
# 						},
# 						accounting_dimensions,
# 					)
# 				)

# 			# Deductions
# 			for acc_cc, amount in deductions.items():
# 				exchange_rate, amt = self.get_amount_and_exchange_rate_for_journal_entry(
# 					acc_cc[0], amount, company_currency, currencies
# 				)
# 				payable_amount -= flt(amount, precision)
# 				accounts.append(
# 					self.update_accounting_dimensions(
# 						{
# 							"account": acc_cc[0],
# 							"credit_in_account_currency": flt(amt, precision),
# 							"exchange_rate": flt(exchange_rate),
# 							"cost_center": acc_cc[1] or self.cost_center,
# 							"project": self.project,
# 						},
# 						accounting_dimensions,
# 					)
# 				)

# 			# Payable amount
# 			exchange_rate, payable_amt = self.get_amount_and_exchange_rate_for_journal_entry(
# 				payroll_payable_account, payable_amount, company_currency, currencies
# 			)
# 			accounts.append(
# 				self.update_accounting_dimensions(
# 					{
# 						"account": payroll_payable_account,
# 						"credit_in_account_currency": flt(payable_amt, precision),
# 						"exchange_rate": flt(exchange_rate),
# 						"cost_center": self.cost_center,
# 					},
# 					accounting_dimensions,
# 				)
# 			)

# 			journal_entry.set("accounts", accounts)
# 			if len(currencies) > 1:
# 				multi_currency = 1
# 			journal_entry.multi_currency = multi_currency
# 			journal_entry.title = payroll_payable_account
# 			journal_entry.save()

# 			try:
# 				journal_entry.submit()
# 				jv_name = journal_entry.name
# 				self.update_salary_slip_status(jv_name=jv_name)
# 			except Exception as e:
# 				if type(e) in (str, list, tuple):
# 					frappe.msgprint(e)
# 				raise

# 		return jv_name

# 	def update_accounting_dimensions(self, row, accounting_dimensions):
# 		for dimension in accounting_dimensions:
# 			row.update({dimension: self.get(dimension)})

# 		return row

# 	def get_amount_and_exchange_rate_for_journal_entry(
# 		self, account, amount, company_currency, currencies
# 	):
# 		conversion_rate = 1
# 		exchange_rate = self.exchange_rate
# 		account_currency = frappe.db.get_value("Account", account, "account_currency")
# 		if account_currency not in currencies:
# 			currencies.append(account_currency)
# 		if account_currency == company_currency:
# 			conversion_rate = self.exchange_rate
# 			exchange_rate = 1
# 		amount = flt(amount) * flt(conversion_rate)
# 		return exchange_rate, amount

# 	@frappe.whitelist()
# 	def make_payment_entry(self):
# 		self.check_permission("write")

# 		salary_slip_name_list = frappe.db.sql(
# 			""" select t1.name from `tabSalary Slip` t1
# 			where t1.docstatus = 1 and start_date >= %s and end_date <= %s and t1.payroll_entry = %s
# 			""",
# 			(self.start_date, self.end_date, self.name),
# 			as_list=True,
# 		)

# 		if salary_slip_name_list and len(salary_slip_name_list) > 0:
# 			salary_slip_total = 0
# 			for salary_slip_name in salary_slip_name_list:
# 				salary_slip = frappe.get_doc("Salary Slip", salary_slip_name[0])
# 				for sal_detail in salary_slip.earnings:
# 					(
# 						is_flexible_benefit,
# 						only_tax_impact,
# 						creat_separate_je,
# 						statistical_component,
# 					) = frappe.db.get_value(
# 						"Salary Component",
# 						sal_detail.salary_component,
# 						[
# 							"is_flexible_benefit",
# 							"only_tax_impact",
# 							"create_separate_payment_entry_against_benefit_claim",
# 							"statistical_component",
# 						],
# 					)
# 					if only_tax_impact != 1 and statistical_component != 1:
# 						if is_flexible_benefit == 1 and creat_separate_je == 1:
# 							self.create_journal_entry(sal_detail.amount, sal_detail.salary_component)
# 						else:
# 							salary_slip_total += sal_detail.amount
# 				for sal_detail in salary_slip.deductions:
# 					statistical_component = frappe.db.get_value(
# 						"Salary Component", sal_detail.salary_component, "statistical_component"
# 					)
# 					if statistical_component != 1:
# 						salary_slip_total -= sal_detail.amount
# 			if salary_slip_total > 0:
# 				self.create_journal_entry(salary_slip_total, "salary")

# 	def create_journal_entry(self, je_payment_amount, user_remark):
# 		payroll_payable_account = self.payroll_payable_account
# 		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

# 		accounts = []
# 		currencies = []
# 		multi_currency = 0
# 		company_currency = erpnext.get_company_currency(self.company)
# 		accounting_dimensions = get_accounting_dimensions() or []

# 		exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
# 			self.payment_account, je_payment_amount, company_currency, currencies
# 		)
# 		accounts.append(
# 			self.update_accounting_dimensions(
# 				{
# 					"account": self.payment_account,
# 					"bank_account": self.bank_account,
# 					"credit_in_account_currency": flt(amount, precision),
# 					"exchange_rate": flt(exchange_rate),
# 				},
# 				accounting_dimensions,
# 			)
# 		)

# 		exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
# 			payroll_payable_account, je_payment_amount, company_currency, currencies
# 		)
# 		accounts.append(
# 			self.update_accounting_dimensions(
# 				{
# 					"account": payroll_payable_account,
# 					"debit_in_account_currency": flt(amount, precision),
# 					"exchange_rate": flt(exchange_rate),
# 					"reference_type": self.doctype,
# 					"reference_name": self.name,
# 				},
# 				accounting_dimensions,
# 			)
# 		)

# 		if len(currencies) > 1:
# 			multi_currency = 1

# 		journal_entry = frappe.new_doc("Journal Entry")
# 		journal_entry.voucher_type = "Bank Entry"
# 		journal_entry.user_remark = _("Payment of {0} from {1} to {2}").format(
# 			user_remark, self.start_date, self.end_date
# 		)
# 		journal_entry.company = self.company
# 		journal_entry.posting_date = self.posting_date
# 		journal_entry.multi_currency = multi_currency

# 		journal_entry.set("accounts", accounts)
# 		journal_entry.save(ignore_permissions=True)

# 	def update_salary_slip_status(self, jv_name=None):
# 		ss_list = self.get_sal_slip_list(ss_status=1)
# 		for ss in ss_list:
# 			ss_obj = frappe.get_doc("Salary Slip", ss[0])
# 			frappe.db.set_value("Salary Slip", ss_obj.name, "journal_entry", jv_name)

# 	def set_start_end_dates(self):
# 		self.update(
# 			get_start_end_dates(self.payroll_frequency, self.start_date or self.posting_date, self.company)
# 		)


# def get_sal_struct(
# 	company: str, currency: str, salary_slip_based_on_timesheet: int, condition: str
# ):
# 	return frappe.db.sql_list(
# 		"""
# 		select
# 			name from `tabSalary Structure`
# 		where
# 			docstatus = 1 and
# 			is_active = 'Yes'
# 			and company = %(company)s
# 			and currency = %(currency)s and
# 			ifnull(salary_slip_based_on_timesheet,0) = %(salary_slip_based_on_timesheet)s
# 			{condition}""".format(
# 			condition=condition
# 		),
# 		{
# 			"company": company,
# 			"currency": currency,
# 			"salary_slip_based_on_timesheet": salary_slip_based_on_timesheet,
# 		},
# 	)


# def get_filter_condition(filters):
# 	cond = ""
# 	for f in ["company", "branch", "department", "designation"]:
# 		if filters.get(f):
# 			cond += " and t1." + f + " = " + frappe.db.escape(filters.get(f))

# 	return cond


# def get_joining_relieving_condition(start_date, end_date):
# 	cond = """
# 		and ifnull(t1.date_of_joining, '1900-01-01') <= '%(end_date)s'
# 		and ifnull(t1.relieving_date, '2199-12-31') >= '%(start_date)s'
# 	""" % {
# 		"start_date": start_date,
# 		"end_date": end_date,
# 	}
# 	return cond


# def get_emp_list(sal_struct, cond, end_date, payroll_payable_account):
# 	return frappe.db.sql(
# 		"""
# 			select
# 				distinct t1.name as employee, t1.employee_name, t1.department, t1.designation
# 			from
# 				`tabEmployee` t1, `tabSalary Structure Assignment` t2
# 			where
# 				t1.name = t2.employee
# 				and t2.docstatus = 1
# 				and t1.status != 'Inactive'
# 		%s order by t2.from_date desc
# 		"""
# 		% cond,
# 		{
# 			"sal_struct": tuple(sal_struct),
# 			"from_date": end_date,
# 			"payroll_payable_account": payroll_payable_account,
# 		},
# 		as_dict=True,
# 	)


# def remove_payrolled_employees(emp_list, start_date, end_date):
# 	new_emp_list = []
# 	for employee_details in emp_list:
# 		if not frappe.db.exists(
# 			"Salary Slip",
# 			{
# 				"employee": employee_details.employee,
# 				"start_date": start_date,
# 				"end_date": end_date,
# 				"docstatus": 1,
# 			},
# 		):
# 			new_emp_list.append(employee_details)

# 	return new_emp_list


# @frappe.whitelist()
# def get_start_end_dates(payroll_frequency, start_date=None, company=None):
# 	"""Returns dict of start and end dates for given payroll frequency based on start_date"""

# 	if payroll_frequency == "Monthly" or payroll_frequency == "Bimonthly" or payroll_frequency == "":
# 		fiscal_year = get_fiscal_year(start_date, company=company)[0]
# 		month = "%02d" % getdate(start_date).month
# 		m = get_month_details(fiscal_year, month)
# 		if payroll_frequency == "Bimonthly":
# 			if getdate(start_date).day <= 15:
# 				start_date = m["month_start_date"]
# 				end_date = m["month_mid_end_date"]
# 			else:
# 				start_date = m["month_mid_start_date"]
# 				end_date = m["month_end_date"]
# 		else:
# 			start_date = m["month_start_date"]
# 			end_date = m["month_end_date"]

# 	if payroll_frequency == "Weekly":
# 		end_date = add_days(start_date, 6)

# 	if payroll_frequency == "Fortnightly":
# 		end_date = add_days(start_date, 13)

# 	if payroll_frequency == "Daily":
# 		end_date = start_date

# 	return frappe._dict({"start_date": start_date, "end_date": end_date})


# def get_frequency_kwargs(frequency_name):
# 	frequency_dict = {
# 		"monthly": {"months": 1},
# 		"fortnightly": {"days": 14},
# 		"weekly": {"days": 7},
# 		"daily": {"days": 1},
# 	}
# 	return frequency_dict.get(frequency_name)


# @frappe.whitelist()
# def get_end_date(start_date, frequency):
# 	start_date = getdate(start_date)
# 	frequency = frequency.lower() if frequency else "monthly"
# 	kwargs = (
# 		get_frequency_kwargs(frequency) if frequency != "bimonthly" else get_frequency_kwargs("monthly")
# 	)

# 	# weekly, fortnightly and daily intervals have fixed days so no problems
# 	end_date = add_to_date(start_date, **kwargs) - relativedelta(days=1)
# 	if frequency != "bimonthly":
# 		return dict(end_date=end_date.strftime(DATE_FORMAT))

# 	else:
# 		return dict(end_date="")


# def get_month_details(year, month):
# 	ysd = frappe.db.get_value("Fiscal Year", year, "year_start_date")
# 	if ysd:
# 		import calendar
# 		import datetime

# 		diff_mnt = cint(month) - cint(ysd.month)
# 		if diff_mnt < 0:
# 			diff_mnt = 12 - int(ysd.month) + cint(month)
# 		msd = ysd + relativedelta(months=diff_mnt)  # month start date
# 		month_days = cint(calendar.monthrange(cint(msd.year), cint(month))[1])  # days in month
# 		mid_start = datetime.date(msd.year, cint(month), 16)  # month mid start date
# 		mid_end = datetime.date(msd.year, cint(month), 15)  # month mid end date
# 		med = datetime.date(msd.year, cint(month), month_days)  # month end date
# 		return frappe._dict(
# 			{
# 				"year": msd.year,
# 				"month_start_date": msd,
# 				"month_end_date": med,
# 				"month_mid_start_date": mid_start,
# 				"month_mid_end_date": mid_end,
# 				"month_days": month_days,
# 			}
# 		)
# 	else:
# 		frappe.throw(_("Fiscal Year {0} not found").format(year))


# def get_payroll_entry_bank_entries(payroll_entry_name):
# 	journal_entries = frappe.db.sql(
# 		"select name from `tabJournal Entry Account` "
# 		'where reference_type="Payroll Entry" '
# 		"and reference_name=%s and docstatus=1",
# 		payroll_entry_name,
# 		as_dict=1,
# 	)

# 	return journal_entries


# @frappe.whitelist()
# def payroll_entry_has_bank_entries(name):
# 	response = {}
# 	bank_entries = get_payroll_entry_bank_entries(name)
# 	response["submitted"] = 1 if bank_entries else 0

# 	return response


# def log_payroll_failure(process, payroll_entry, error):
# 	error_log = frappe.log_error(
# 		title=_("Salary Slip {0} failed for Payroll Entry {1}").format(process, payroll_entry.name)
# 	)
# 	message_log = frappe.message_log.pop() if frappe.message_log else str(error)

# 	try:
# 		error_message = json.loads(message_log).get("message")
# 	except Exception:
# 		error_message = message_log

# 	error_message += "\n" + _("Check Error Log {0} for more details.").format(
# 		get_link_to_form("Error Log", error_log.name)
# 	)

# 	payroll_entry.db_set({"error_message": error_message, "status": "Failed"})


# def create_salary_slips_for_employees(employees, args, publish_progress=True):
# 	try:
# 		payroll_entry = frappe.get_doc("Payroll Entry", args.payroll_entry)
# 		salary_slips_exist_for = get_existing_salary_slips(employees, args)
# 		count = 0

# 		for emp in employees:
# 			if emp not in salary_slips_exist_for:
# 				args.update({"doctype": "Salary Slip", "employee": emp})
# 				frappe.get_doc(args).insert()

# 				count += 1
# 				if publish_progress:
# 					frappe.publish_progress(
# 						count * 100 / len(set(employees) - set(salary_slips_exist_for)),
# 						title=_("Creating Salary Slips..."),
# 					)

# 		payroll_entry.db_set({"status": "Submitted", "salary_slips_created": 1, "error_message": ""})

# 		if salary_slips_exist_for:
# 			frappe.msgprint(
# 				_(
# 					"Salary Slips already exist for employees {}, and will not be processed by this payroll."
# 				).format(frappe.bold(", ".join(emp for emp in salary_slips_exist_for))),
# 				title=_("Message"),
# 				indicator="orange",
# 			)

# 	except Exception as e:
# 		frappe.db.rollback()
# 		log_payroll_failure("creation", payroll_entry, e)

# 	finally:
# 		frappe.db.commit()  # nosemgrep
# 		frappe.publish_realtime("completed_salary_slip_creation")


# def show_payroll_submission_status(submitted, unsubmitted, payroll_entry):
# 	if not submitted and not unsubmitted:
# 		frappe.msgprint(
# 			_(
# 				"No salary slip found to submit for the above selected criteria OR salary slip already submitted"
# 			)
# 		)
# 	elif submitted and not unsubmitted:
# 		frappe.msgprint(
# 			_("Salary Slips submitted for period from {0} to {1}").format(
# 				payroll_entry.start_date, payroll_entry.end_date
# 			)
# 		)
# 	elif unsubmitted:
# 		frappe.msgprint(
# 			_("Could not submit some Salary Slips: {}").format(
# 				", ".join(get_link_to_form("Salary Slip", entry) for entry in unsubmitted)
# 			)
# 		)


# def get_existing_salary_slips(employees, args):
# 	return frappe.db.sql_list(
# 		"""
# 		select distinct employee from `tabSalary Slip`
# 		where docstatus!= 2 and company = %s and payroll_entry = %s
# 			and start_date >= %s and end_date <= %s
# 			and employee in (%s)
# 	"""
# 		% ("%s", "%s", "%s", "%s", ", ".join(["%s"] * len(employees))),
# 		[args.company, args.payroll_entry, args.start_date, args.end_date] + employees,
# 	)


# def submit_salary_slips_for_employees(payroll_entry, salary_slips, publish_progress=True):
# 	try:
# 		submitted = []
# 		unsubmitted = []
# 		frappe.flags.via_payroll_entry = True
# 		count = 0

# 		for entry in salary_slips:
# 			salary_slip = frappe.get_doc("Salary Slip", entry[0])
# 			if salary_slip.net_pay < 0:
# 				unsubmitted.append(entry[0])
# 			else:
# 				try:
# 					salary_slip.submit()
# 					submitted.append(salary_slip)
# 				except frappe.ValidationError:
# 					unsubmitted.append(entry[0])

# 			count += 1
# 			if publish_progress:
# 				frappe.publish_progress(count * 100 / len(salary_slips), title=_("Submitting Salary Slips..."))

# 		if submitted:
# 			payroll_entry.make_accrual_jv_entry()
# 			payroll_entry.email_salary_slip(submitted)
# 			payroll_entry.db_set({"salary_slips_submitted": 1, "status": "Submitted", "error_message": ""})

# 		show_payroll_submission_status(submitted, unsubmitted, payroll_entry)

# 	except Exception as e:
# 		frappe.db.rollback()
# 		log_payroll_failure("submission", payroll_entry, e)

# 	finally:
# 		frappe.db.commit()  # nosemgrep
# 		frappe.publish_realtime("completed_salary_slip_submission")

# 	frappe.flags.via_payroll_entry = False


# @frappe.whitelist()
# @frappe.validate_and_sanitize_search_inputs
# def get_payroll_entries_for_jv(doctype, txt, searchfield, start, page_len, filters):
# 	return frappe.db.sql(
# 		"""
# 		select name from `tabPayroll Entry`
# 		where `{key}` LIKE %(txt)s
# 		and name not in
# 			(select reference_name from `tabJournal Entry Account`
# 				where reference_type="Payroll Entry")
# 		order by name limit %(start)s, %(page_len)s""".format(
# 			key=searchfield
# 		),
# 		{"txt": "%%%s%%" % txt, "start": start, "page_len": page_len},
# 	)


# def get_employee_list(filters: frappe._dict) -> list[str]:
# 	condition = f"and payroll_frequency = '{filters.payroll_frequency}'"

# 	sal_struct = get_sal_struct(
# 		filters.company, filters.currency, filters.salary_slip_based_on_timesheet, condition
# 	)

# 	if not sal_struct:
# 		return []

# 	cond = (
# 		get_filter_condition(filters)
# 		+ get_joining_relieving_condition(filters.start_date, filters.end_date)
# 		+ (
# 			"and t2.salary_structure IN %(sal_struct)s "
# 			"and t2.payroll_payable_account = %(payroll_payable_account)s "
# 			"and %(from_date)s >= t2.from_date"
# 		)
# 	)
# 	emp_list = get_emp_list(sal_struct, cond, filters.end_date, filters.payroll_payable_account)
# 	return remove_payrolled_employees(emp_list, filters.start_date, filters.end_date)


# @frappe.whitelist()
# @frappe.validate_and_sanitize_search_inputs
# def employee_query(doctype, txt, searchfield, start, page_len, filters):
# 	filters = frappe._dict(filters)
# 	conditions = []
# 	include_employees = []
# 	emp_cond = ""

# 	if not filters.payroll_frequency:
# 		frappe.throw(_("Select Payroll Frequency."))

# 	if filters.start_date and filters.end_date:
# 		employee_list = get_employee_list(filters)
# 		emp = filters.get("employees") or []
# 		include_employees = [
# 			employee.employee for employee in employee_list if employee.employee not in emp
# 		]
# 		filters.pop("start_date")
# 		filters.pop("end_date")
# 		filters.pop("salary_slip_based_on_timesheet")
# 		filters.pop("payroll_frequency")
# 		filters.pop("payroll_payable_account")
# 		filters.pop("currency")
# 		if filters.employees is not None:
# 			filters.pop("employees")

# 		if include_employees:
# 			emp_cond += "and employee in %(include_employees)s"

# 	return frappe.db.sql(
# 		"""select name, employee_name from `tabEmployee`
# 		where status = 'Active'
# 			and docstatus < 2
# 			and ({key} like %(txt)s
# 				or employee_name like %(txt)s)
# 			{emp_cond}
# 			{fcond} {mcond}
# 		order by
# 			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
# 			if(locate(%(_txt)s, employee_name), locate(%(_txt)s, employee_name), 99999),
# 			idx desc,
# 			name, employee_name
# 		limit %(start)s, %(page_len)s""".format(
# 			**{
# 				"key": searchfield,
# 				"fcond": get_filters_cond(doctype, filters, conditions),
# 				"mcond": get_match_cond(doctype),
# 				"emp_cond": emp_cond,
# 			}
# 		),
# 		{
# 			"txt": "%%%s%%" % txt,
# 			"_txt": txt.replace("%", ""),
# 			"start": start,
# 			"page_len": page_len,
# 			"include_employees": include_employees,
# 		},
# 	)
