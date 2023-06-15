# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate, rounded, date_diff, money_in_words
from frappe.model.naming import make_autoname

from frappe import msgprint, _
from erpnext.accounts.utils import get_fiscal_year
from hrms.hr.utils import set_employee_name
from hrms.hr.hr_custom_functions import get_month_details
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.utilities.transaction_base import TransactionBase
from frappe.model.mapper import get_mapped_doc
from erpnext import get_company_currency

class SalarySlip(TransactionBase):
	def autoname(self):
		self.name = make_autoname(self.employee + '/SSL/' + self.fiscal_year + self.month + '/.#####')

	def validate(self):
		set_employee_name(self)
		self.validate_dates()
		self.check_existing()
		self.set_month_dates()
		#Commented by SHIV on 2018/09/28
		'''
		if not (len(self.get("earnings")) or len(self.get("deductions"))):
			self.get_emp_and_leave_details()
		else:
			self.get_leave_details(lwp = self.leave_without_pay)
		'''
		self.get_emp_and_leave_details()        #Added by SHIV on 2018/09/28
		#Following code commented by SHIV on 2018/10/15
		'''
		if self.salary_slip_based_on_timesheet or not self.net_pay:
		self.calculate_net_pay()
		'''

		self.calculate_net_pay()                #Added by SHIV on 2018/10/15
		self.validate_amounts()                 #Added by SHIV on 2018/10/15
		company_currency = get_company_currency(self.company)
		self.total_in_words = money_in_words(self.rounded_total, company_currency)
		self.check_house_rent_deduction()

	def validate_dates(self):
		if date_diff(self.end_date, self.start_date) < 0:
			frappe.throw(_("To date cannot be before From date"))

	@frappe.whitelist()
	def get_emp_and_leave_details(self):
		payment_days = 0                #Added by SHIV on 2018/09/28
		if self.employee:
			self.set("earnings", [])
			self.set("deductions", [])
			self.set('ot_items', []) #Added by Kinley on 2022/11/26
			self.set("items", [])   #Added by SHIV on 2018/09/28
			self.set_month_dates()
			self.validate_dates()
			self.yearmonth = str(self.fiscal_year)+str(self.month)
			joining_date, relieving_date = frappe.db.get_value("Employee", self.employee, ["date_of_joining", "relieving_date"])
			struct = self.check_sal_struct(joining_date, relieving_date)

			if struct:
				for st in struct:
					ss_doc = frappe.get_doc('Salary Structure', st.name)
					self.salary_slip_based_on_timesheet = ss_doc.salary_slip_based_on_timesheet or 0
					self.set_time_sheet()
					calc_days = self.get_leave_details(joining_date, relieving_date, ss_doc)
					if calc_days:
						self.pull_sal_struct(ss_doc, calc_days)

	def check_house_rent_deduction(self):
		salary_structure = ""
		for b in self.items:
			salary_structure = b.salary_structure
		for a in self.deductions:
			if a.salary_component == "House Rent Deduction":
				if salary_structure != "":
					a.hr_rate = frappe.db.get_value("Salary Detail",{"parent":salary_structure,"salary_component":"House Rent Deduction"},"hr_rate")
					a.place = frappe.db.get_value("Salary Detail",{"parent":salary_structure,"salary_component":"House Rent Deduction"},"place")
					a.town = frappe.db.get_value("Salary Detail",{"parent":salary_structure,"salary_component":"House Rent Deduction"},"town")
					a.sqr_ft = frappe.db.get_value("Salary Detail",{"parent":salary_structure,"salary_component":"House Rent Deduction"},"sqr_ft")

	def set_time_sheet(self):
		if self.salary_slip_based_on_timesheet:
			self.set("timesheets", [])
			timesheets = frappe.db.sql(""" select * from `tabTimesheet` where employee = %(employee)s and start_date BETWEEN %(start_date)s AND %(end_date)s and (status = 'Submitted' or
				status = 'Billed')""", {'employee': self.employee, 'start_date': self.start_date, 'end_date': self.end_date}, as_dict=1)

			for data in timesheets:
				self.append('timesheets', {
					'time_sheet': data.name,
					'working_hours': data.total_hours
				})

	def set_month_dates(self):
		if self.month and not self.salary_slip_based_on_timesheet:
			m = get_month_details(self.fiscal_year, self.month)
			self.start_date = m['month_start_date']
			self.end_date = m['month_end_date']

	def check_sal_struct(self, joining_date, relieving_date):
		struct = frappe.db.sql("""select name from `tabSalary Structure`
			where employee = %s
			and from_date <= %s
			and ifnull(to_date, %s) >= %s
			order by from_date
			""",(self.employee, self.end_date, self.end_date, self.start_date), as_dict=True)
 
		if not struct:
			self.salary_structure = None
			frappe.throw(_('No active or default Salary Structure found for employee <a href="#Form/Employee/{0}">{0} {1}</a> for the given dates')
				.format(self.employee, self.employee_name), title=_('Salary Structure Missing'))
		return struct 

	def pull_sal_struct(self, ss_doc, calc_days):                
		from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip
		make_salary_slip(ss_doc.name, self, calc_days)

		if self.salary_slip_based_on_timesheet:
			self.salary_structure = ss_doc.name
			self.hour_rate = ss_doc.hour_rate
			self.total_working_hours = sum([d.working_hours or 0.0 for d in self.timesheets]) or 0.0
			self.add_earning_for_hourly_wages(ss_doc.salary_component)

	def add_earning_for_hourly_wages(self, salary_component):
		default_type = False
		for data in self.earnings:
			if data.salary_component == salary_component:
				data.amount = self.hour_rate * self.total_working_hours
				default_type = True
				break

		if not default_type:
			earnings = self.append('earnings', {})
			earnings.salary_component = salary_component
			earnings.amount = self.hour_rate * self.total_working_hours

	def pull_emp_details(self):
		emp = frappe.get_doc("Employee",self.employee)
		self.branch             = emp.branch
		self.department         = emp.department
		self.division           = emp.division
		self.cost_center        = emp.cost_center
		self.designation        = emp.designation
		self.section            = emp.section
		self.employee_subgroup  = emp.grade
		self.bank_name          = emp.bank_name
		self.bank_account_no    = emp.bank_ac_no
		self.gis_number         = emp.gis_number
		self.gis_policy_number  = emp.gis_policy_number
		self.employment_type    = emp.employment_type
		self.employee_group     = emp.employee_group
		self.employee_grade     = emp.grade
		self.business_activity  = emp.business_activity
			
	def get_leave_details(self, joining_date=None, relieving_date=None, ss_doc=None, lwp=None):
		days_in_month= 0
		working_days = 0
		holidays     = 0
		payment_days = 0
		lwp          = 0
		start_date   = getdate(self.start_date)
		end_date     = getdate(self.end_date)
			
		# if default fiscal year is not set, get from nowdate
		if not self.fiscal_year:
			self.fiscal_year = get_fiscal_year(nowdate())[0]

		if not self.month:
			self.month = "%02d" % getdate(nowdate()).month
			self.set_month_dates()

		if not joining_date:
			joining_date, relieving_date = frappe.db.get_value("Employee", self.employee,
				["date_of_joining", "relieving_date"])

		if ss_doc:
			if getdate(ss_doc.from_date) > start_date:
					start_date = getdate(ss_doc.from_date)

			if ss_doc.to_date:
					if getdate(ss_doc.to_date) < end_date:
							end_date = getdate(ss_doc.to_date)

			if joining_date:
					if joining_date > end_date:
							return {}
					elif joining_date > start_date:
							start_date = joining_date

			if relieving_date:
					if relieving_date < start_date:
							return {}
					elif relieving_date < end_date:
							end_date = relieving_date

			if end_date < start_date:
					return {}
			else:
					days_in_month= date_diff(self.end_date, self.start_date) + 1
					holidays     = self.get_holidays_for_employee(self.start_date, self.end_date)
					working_days = date_diff(end_date, start_date) + 1
					calc_holidays= self.get_holidays_for_employee(start_date, end_date)
					lwp          = self.calculate_lwp(holidays, start_date, end_date)
					
					if not cint(frappe.db.get_value("HR Settings", None, "include_holidays_in_total_working_days")):
							days_in_month -= len(holidays)
							working_days  -= len(calc_holidays)

					payment_days = flt(working_days)-flt(lwp) 

		self.total_days_in_month = days_in_month
		self.leave_without_pay = lwp
		self.payment_days = payment_days > 0 and payment_days or 0

		self.append('items',{
				'salary_structure': ss_doc.name,
				'from_date': start_date,
				'to_date': end_date,
				'total_days_in_month': days_in_month,
				'working_days': working_days,
				'leave_without_pay': lwp,
				'payment_days': payment_days
		})
		return {
				'salary_structure': ss_doc.name,
				'from_date': start_date,
				'to_date': end_date,
				'total_days_in_month': days_in_month,
				'working_days': working_days,
				'leave_without_pay': lwp,
				'payment_days': payment_days
		}
	
	def get_payment_days(self, joining_date, relieving_date):
		start_date = getdate(self.start_date)

		if joining_date:
			if joining_date > getdate(self.start_date):
				start_date = joining_date
			elif joining_date > getdate(self.end_date):
				return

		end_date = getdate(self.end_date)
		if relieving_date:
			if relieving_date > start_date and relieving_date < getdate(self.end_date):
				end_date = relieving_date
			elif relieving_date < getdate(self.start_date):
				frappe.throw(_("Employee relieved on {0} must be set as 'Left'")
					.format(relieving_date))

		payment_days = date_diff(end_date, start_date) + 1

		if not cint(frappe.db.get_value("HR Settings", None, "include_holidays_in_total_working_days")):
			holidays = self.get_holidays_for_employee(start_date, end_date)
			payment_days -= len(holidays)

		return payment_days

	def get_holidays_for_employee(self, start_date, end_date):
		holiday_list = get_holiday_list_for_employee(self.employee)
		holidays = frappe.db.sql_list('''select holiday_date from `tabHoliday`
			where
				parent=%(holiday_list)s
				and holiday_date >= %(start_date)s
				and holiday_date <= %(end_date)s''', {
					"holiday_list": holiday_list,
					"start_date": start_date,
					"end_date": end_date
				})

		holidays = [cstr(i) for i in holidays]

		return holidays

		#Added by SHIV on 2018/09/28
	def calculate_lwp(self, holidays, start_date, end_date):
		lwp = 0
		for d in range(cint(getdate(start_date).day)-1,cint(getdate(end_date).day)):
			dt = add_days(cstr(self.start_date), d)
			if dt not in holidays:
				leave = frappe.db.sql("""
					select t1.name, t1.half_day
					from `tabLeave Application` t1, `tabLeave Type` t2
					where t2.name = t1.leave_type
					and t2.is_lwp = 1
					and t1.docstatus = 1
					and t1.employee = %s
					and %s between from_date and to_date
				""", (self.employee, dt))
				if leave:
					lwp = cint(leave[0][1]) and (lwp + 0.5) or (lwp + 1)
		return lwp

		#Commented by SHIV on 2018/09/28
		'''
	def calculate_lwp(self, holidays, working_days):
		lwp = 0
		for d in range(working_days):
			dt = add_days(cstr(self.start_date), d)
			if dt not in holidays:
				leave = frappe.db.sql("""
					select t1.name, t1.half_day
					from `tabLeave Application` t1, `tabLeave Type` t2
					where t2.name = t1.leave_type
					and t2.is_lwp = 1
					and t1.docstatus = 1
					and t1.employee = %s
					and %s between from_date and to_date
				""", (self.employee, dt))
				if leave:
					lwp = cint(leave[0][1]) and (lwp + 0.5) or (lwp + 1)
		return lwp
	'''

	def check_existing(self):
		if not self.salary_slip_based_on_timesheet:
			ret_exist = frappe.db.sql("""select name from `tabSalary Slip`
						where month = %s and fiscal_year = %s and docstatus != 2
						and employee = %s and name != %s""",
						(self.month, self.fiscal_year, self.employee, self.name))
			if ret_exist:
				frappe.throw(_('Salary Slip already created for employee <a href="#Form/Employee/{0}">{0} {1}</a>').format(self.employee, self.employee_name))
		else:
			for data in self.timesheets:
				if frappe.db.get_value('Timesheet', data.time_sheet, 'status') == 'Payrolled':
					frappe.throw(_("Salary Slip of employee {0} already created for time sheet {1}").format(self.employee, data.time_sheet))

	def calculate_earning_total(self):
		self.gross_pay = flt(self.arrear_amount) + flt(self.leave_encashment_amount)
		self.actual_basic = 0
		for d in self.get("earnings"):
			# Added by SHIV on 2018/09/24
			if d.salary_component == 'Basic Pay':
				if flt(d.total_days_in_month) != (flt(d.working_days)):
							self.actual_basic = flt(self.actual_basic) + flt(d.default_amount)
					
			# Commented by SHIV on 2018/09/24
			'''
			if cint(d.depends_on_lwp) == 1 and not self.salary_slip_based_on_timesheet:
				d.amount = rounded((flt(d.default_amount) * flt(self.payment_days)
					/ cint(self.total_days_in_month)), self.precision("amount", "earnings"))
			elif not self.payment_days and not self.salary_slip_based_on_timesheet:
				d.amount = 0
			elif not d.amount:
				d.amount = d.default_amount
			'''
			self.gross_pay += flt(d.amount)

	def calculate_ded_total(self):
		self.total_deduction = 0
		for d in self.get('deductions'):
			# Commented by SHIV on 2018/09/24
			'''
			if cint(d.depends_on_lwp) == 1 and not self.salary_slip_based_on_timesheet:
				d.amount = rounded((flt(d.amount) * flt(self.payment_days)
					/ cint(self.total_days_in_month)), self.precision("amount", "deductions"))
			elif not self.payment_days and not self.salary_slip_based_on_timesheet:
				d.amount = 0
			elif not d.amount:
				d.amount = d.default_amount
			'''
			self.total_deduction += flt(d.amount)

	def calculate_net_pay(self):
		disable_rounded_total = cint(frappe.db.get_value("Global Defaults", None, "disable_rounded_total"))

		self.calculate_earning_total()
		self.calculate_ded_total()
		self.net_pay = flt(self.gross_pay) - flt(self.total_deduction)
		self.rounded_total = rounded(self.net_pay,
			self.precision("net_pay") if disable_rounded_total else 0)

	#Added by SHIV on 2018/10/15
	def validate_amounts(self):
		if flt(self.net_pay) < 0:
			frappe.throw(_('Net pay cannot be a negative value for employee <a href="#Form/Employee/{0}">{0} {1}</a>').format(self.employee, self.employee_name),title="Invalid Data")

	def on_submit(self):
		self.update_status(self.name)
		self.update_deduction_balance()
		self.post_sws_entry()
		self.update_ot()


	def update_ot(self, cancel = False):
		processed = 1
		ss_name = self.name
		if cancel:
			processed = 0
			ss_name = ''
		for a in self.ot_items:
			frappe.db.sql(""" update `tabOvertime Application` set processed = '{0}', salary_slip = '{3}'  where name = '{1}' and employee = '{2}' 
		""".format(processed, a.reference, self.employee, ss_name))

	def post_sws_entry(self):
		sws = frappe.db.get_single_value("SWS Settings", "salary_component")
		amount = 0
		for a in self.deductions:
			if a.salary_component == sws:
				amount = a.amount
		if not amount:
			return

		doc = frappe.new_doc("SWS Entry")
		doc.flags.ignore_permissions = 1
		doc.posting_date = nowdate()
		doc.branch = self.branch
		doc.ref_doc = self.name
		doc.employee = self.employee
		doc.credit = amount
		doc.fiscal_year = self.fiscal_year
		doc.month = self.month
		doc.submit()
				
	def on_cancel(self):
		self.update_status()
		self.update_deduction_balance()
		self.delete_sws_entry()
		self.update_ot(cancel = True)

	def delete_sws_entry(self):
		frappe.db.sql("delete from `tabSWS Entry` where ref_doc = %s", self.name)
	
	# def update_outstanding_amount_in_btl_sales(self):
	# 	# added by biren on 09/11/2021
	# 	for item in self.deductions:

	def update_deduction_balance(self):
			for ssl in self.deductions:
					if (ssl.ref_docname and ssl.amount and ssl.total_deductible_amount):
							sst = frappe.get_doc("Salary Detail", ssl.ref_docname)
							if sst:
									sst.total_deducted_amount    += (-1*flt(ssl.amount) if self.docstatus == 2 else flt(ssl.amount))
									sst.total_outstanding_amount -= (-1*flt(ssl.amount) if self.docstatus == 2 else flt(ssl.amount))
									sst.save()
					if (ssl.salary_component == 'BTL Sales' and ssl.amount and ssl.reference_number):
						ref_doc = frappe.get_doc("BTL Sales",ssl.reference_number)
						if self.docstatus == 1 and ref_doc.status != 'Paid' and ref_doc.docstatus == 1 :
							bal = ssl.total_outstanding_amount
						elif self.docstatus == 2 and ref_doc.docstatus == 1:
							bal = flt(ssl.total_outstanding_amount) + flt(ssl.amount)

						# frappe.db.set_value("BTL Sales", ssl.reference_number, 'outstanding_amount', bal)
						ref_doc.outstanding_amount = bal
						ref_doc.set_status(update=True)
						ref_doc.save(ignore_permissions=True)

	def email_salary_slip(self):
		# receiver = frappe.db.get_value("Employee", self.employee, "company_email") or \
		# 	frappe.db.get_value("Employee", self.employee, "personal_email")
		# if receiver:
		# 	subj = 'Salary Slip - from {0} to {1}, fiscal year {2}'.format(self.start_date, self.end_date, self.fiscal_year)
		# 	frappe.sendmail([receiver], subject=subj, message = _("Please see attachment"),
		# 		attachments=[frappe.attach_print(self.doctype, self.name, file_name=self.name)], reference_doctype= self.doctype, reference_name= self.name)
		# else:
		# 	msgprint(_("{0}: Employee email not found, hence email not sent").format(self.employee_name))
		pass

	def update_status(self, salary_slip=None):
		for data in self.timesheets:
			if data.time_sheet:
				timesheet = frappe.get_doc('Timesheet', data.time_sheet)
				timesheet.salary_slip = salary_slip
				timesheet.flags.ignore_validate_update_after_submit = True
				timesheet.set_status()
				timesheet.save()
				
def unlink_ref_doc_from_salary_slip(doc, method=None):
	"""Unlinks accrual Journal Entry from Salary Slips on cancellation"""
	linked_ss = frappe.db.sql_list(
		"""select name from `tabSalary Slip`
	where journal_entry=%s and docstatus < 2""",
		(doc.name),
	)
	if linked_ss:
		for ss in linked_ss:
			ss_doc = frappe.get_doc("Salary Slip", ss)
			frappe.db.set_value("Salary Slip", ss_doc.name, "journal_entry", "")

# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if "HR User" in user_roles or "HR Manager" in user_roles:
		return
	else:
		return """(
			exists(select 1
				from `tabEmployee` as e
				where e.name = `tabSalary Slip`.employee
				and e.user_id = '{user}')
		)""".format(user=user)

# Following code added by SHIV on 2020/09/21
def has_record_permission(doc, user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)
	
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return True
	else:
		if frappe.db.exists("Employee", {"name":doc.employee, "user_id": user}):
			return True
		else:
			return False 

	return True

@frappe.whitelist()
def make_last_pay_certificate(source_name, target_doc=None, skip_item_mapping=False):
	def set_missing_values(source, target):
		# frappe.throw(str(target))
		target.salary_slip_id = source.name
		if len(source.earnings) > 0:
			for a in source.earnings:
				earning = target.append("earnings",{})
				earning.salary_component = a.salary_component
				earning.amount = a.amount

		if len(source.deductions) > 0:
			for a in source.deductions:
				deduction = target.append("deductions",{})
				deduction.salary_component = a.salary_component
				deduction.amount = a.amount
				deduction.institution_name = a.institution_name
		ltc = frappe.db.sql("""
			select parent from `tabLTC Details` where employee = '{0}'
			and docstatus = 1 order by creation desc limit 1
		""".format(source.employee),as_dict=1)
		if ltc:
			target.ltc_paid = ltc[0].parent
	
	
	mapper = {
		"Salary Slip": {
			"doctype": "Last Pay Certificate",
		}
	}
	target_doc = get_mapped_doc("Salary Slip", source_name, mapper, target_doc, set_missing_values)

	return target_doc



































# import datetime
# import math

# import frappe
# from frappe import _, msgprint
# from frappe.model.naming import make_autoname
# from frappe.utils import (
# 	add_days,
# 	cint,
# 	cstr,
# 	date_diff,
# 	flt,
# 	formatdate,
# 	get_first_day,
# 	getdate,
# 	money_in_words,
# 	rounded,
# )
# from frappe.utils.background_jobs import enqueue

# import erpnext
# from erpnext.accounts.utils import get_fiscal_year
# from erpnext.loan_management.doctype.loan_repayment.loan_repayment import (
# 	calculate_amounts,
# 	create_repayment_entry,
# )
# from erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import (
# 	process_loan_interest_accrual_for_term_loans,
# )
# from erpnext.utilities.transaction_base import TransactionBase

# from hrms.hr.utils import get_holiday_dates_for_employee, validate_active_employee
# from hrms.payroll.doctype.additional_salary.additional_salary import get_additional_salaries
# from hrms.payroll.doctype.employee_benefit_application.employee_benefit_application import (
# 	get_benefit_component_amount,
# )
# from hrms.payroll.doctype.employee_benefit_claim.employee_benefit_claim import (
# 	get_benefit_claim_amount,
# 	get_last_payroll_period_benefits,
# )
# from hrms.payroll.doctype.payroll_entry.payroll_entry import get_start_end_dates
# from hrms.payroll.doctype.payroll_period.payroll_period import (
# 	get_payroll_period,
# 	get_period_factor,
# )


# class SalarySlip(TransactionBase):
# 	def __init__(self, *args, **kwargs):
# 		super(SalarySlip, self).__init__(*args, **kwargs)
# 		self.series = "Sal Slip/{0}/.#####".format(self.employee)
# 		self.whitelisted_globals = {
# 			"int": int,
# 			"float": float,
# 			"long": int,
# 			"round": round,
# 			"date": datetime.date,
# 			"getdate": getdate,
# 		}

# 	def autoname(self):
# 		self.name = make_autoname(self.series)

# 	def validate(self):
# 		self.status = self.get_status()
# 		validate_active_employee(self.employee)
# 		self.validate_dates()
# 		self.check_existing()
# 		if not self.salary_slip_based_on_timesheet:
# 			self.get_date_details()

# 		if not (len(self.get("earnings")) or len(self.get("deductions"))):
# 			# get details from salary structure
# 			self.get_emp_and_working_day_details()
# 		else:
# 			self.get_working_days_details(lwp=self.leave_without_pay)

# 		self.calculate_net_pay()
# 		self.compute_year_to_date()
# 		self.compute_month_to_date()
# 		self.compute_component_wise_year_to_date()
# 		self.add_leave_balances()

# 		if frappe.db.get_single_value("Payroll Settings", "max_working_hours_against_timesheet"):
# 			max_working_hours = frappe.db.get_single_value(
# 				"Payroll Settings", "max_working_hours_against_timesheet"
# 			)
# 			if self.salary_slip_based_on_timesheet and (self.total_working_hours > int(max_working_hours)):
# 				frappe.msgprint(
# 					_("Total working hours should not be greater than max working hours {0}").format(
# 						max_working_hours
# 					),
# 					alert=True,
# 				)

# 	def set_net_total_in_words(self):
# 		doc_currency = self.currency
# 		company_currency = erpnext.get_company_currency(self.company)
# 		total = self.net_pay if self.is_rounding_total_disabled() else self.rounded_total
# 		base_total = self.base_net_pay if self.is_rounding_total_disabled() else self.base_rounded_total
# 		self.total_in_words = money_in_words(total, doc_currency)
# 		self.base_total_in_words = money_in_words(base_total, company_currency)

# 	def on_submit(self):
# 		if self.net_pay < 0:
# 			frappe.throw(_("Net Pay cannot be less than 0"))
# 		else:
# 			self.set_status()
# 			self.update_status(self.name)
# 			self.make_loan_repayment_entry()
# 			if (
# 				frappe.db.get_single_value("Payroll Settings", "email_salary_slip_to_employee")
# 			) and not frappe.flags.via_payroll_entry:
# 				self.email_salary_slip()

# 		self.update_payment_status_for_gratuity()

# 	def update_payment_status_for_gratuity(self):
# 		additional_salary = frappe.db.get_all(
# 			"Additional Salary",
# 			filters={
# 				"payroll_date": ("between", [self.start_date, self.end_date]),
# 				"employee": self.employee,
# 				"ref_doctype": "Gratuity",
# 				"docstatus": 1,
# 			},
# 			fields=["ref_docname", "name"],
# 			limit=1,
# 		)

# 		if additional_salary:
# 			status = "Paid" if self.docstatus == 1 else "Unpaid"
# 			if additional_salary[0].name in [entry.additional_salary for entry in self.earnings]:
# 				frappe.db.set_value("Gratuity", additional_salary[0].ref_docname, "status", status)

# 	def on_cancel(self):
# 		self.set_status()
# 		self.update_status()
# 		self.update_payment_status_for_gratuity()
# 		self.cancel_loan_repayment_entry()

# 	def on_trash(self):
# 		from frappe.model.naming import revert_series_if_last

# 		revert_series_if_last(self.series, self.name)

# 	def get_status(self):
# 		if self.docstatus == 0:
# 			status = "Draft"
# 		elif self.docstatus == 1:
# 			status = "Submitted"
# 		elif self.docstatus == 2:
# 			status = "Cancelled"
# 		return status

# 	def validate_dates(self, joining_date=None, relieving_date=None):
# 		if date_diff(self.end_date, self.start_date) < 0:
# 			frappe.throw(_("To date cannot be before From date"))

# 		if not joining_date:
# 			joining_date, relieving_date = frappe.get_cached_value(
# 				"Employee", self.employee, ("date_of_joining", "relieving_date")
# 			)

# 		if date_diff(self.end_date, joining_date) < 0:
# 			frappe.throw(_("Cannot create Salary Slip for Employee joining after Payroll Period"))

# 		if relieving_date and date_diff(relieving_date, self.start_date) < 0:
# 			frappe.throw(_("Cannot create Salary Slip for Employee who has left before Payroll Period"))

# 	def is_rounding_total_disabled(self):
# 		return cint(frappe.db.get_single_value("Payroll Settings", "disable_rounded_total"))

# 	def check_existing(self):
# 		if not self.salary_slip_based_on_timesheet:
# 			cond = ""
# 			if self.payroll_entry:
# 				cond += "and payroll_entry = '{0}'".format(self.payroll_entry)
# 			ret_exist = frappe.db.sql(
# 				"""select name from `tabSalary Slip`
# 						where start_date = %s and end_date = %s and docstatus != 2
# 						and employee = %s and name != %s {0}""".format(
# 					cond
# 				),
# 				(self.start_date, self.end_date, self.employee, self.name),
# 			)
# 			if ret_exist:
# 				frappe.throw(
# 					_("Salary Slip of employee {0} already created for this period").format(self.employee)
# 				)
# 		else:
# 			for data in self.timesheets:
# 				if frappe.db.get_value("Timesheet", data.time_sheet, "status") == "Payrolled":
# 					frappe.throw(
# 						_("Salary Slip of employee {0} already created for time sheet {1}").format(
# 							self.employee, data.time_sheet
# 						)
# 					)

# 	def get_date_details(self):
# 		if not self.end_date:
# 			date_details = get_start_end_dates(self.payroll_frequency, self.start_date or self.posting_date)
# 			self.start_date = date_details.start_date
# 			self.end_date = date_details.end_date

# 	@frappe.whitelist()
# 	def get_emp_and_working_day_details(self):
# 		"""First time, load all the components from salary structure"""
# 		if self.employee:
# 			self.set("earnings", [])
# 			self.set("deductions", [])

# 			if not self.salary_slip_based_on_timesheet:
# 				self.get_date_details()

# 			joining_date, relieving_date = frappe.get_cached_value(
# 				"Employee", self.employee, ("date_of_joining", "relieving_date")
# 			)

# 			self.validate_dates(joining_date, relieving_date)

# 			# getin leave details
# 			self.get_working_days_details(joining_date, relieving_date)
# 			struct = self.check_sal_struct(joining_date, relieving_date)

# 			if struct:
# 				self._salary_structure_doc = frappe.get_doc("Salary Structure", struct)
# 				self.salary_slip_based_on_timesheet = (
# 					self._salary_structure_doc.salary_slip_based_on_timesheet or 0
# 				)
# 				self.set_time_sheet()
# 				self.pull_sal_struct()
# 				ps = frappe.db.get_value(
# 					"Payroll Settings", None, ["payroll_based_on", "consider_unmarked_attendance_as"], as_dict=1
# 				)
# 				return [ps.payroll_based_on, ps.consider_unmarked_attendance_as]

# 	def set_time_sheet(self):
# 		if self.salary_slip_based_on_timesheet:
# 			self.set("timesheets", [])
# 			timesheets = frappe.db.sql(
# 				""" select * from `tabTimesheet` where employee = %(employee)s and start_date BETWEEN %(start_date)s AND %(end_date)s and (status = 'Submitted' or
# 				status = 'Billed')""",
# 				{"employee": self.employee, "start_date": self.start_date, "end_date": self.end_date},
# 				as_dict=1,
# 			)

# 			for data in timesheets:
# 				self.append("timesheets", {"time_sheet": data.name, "working_hours": data.total_hours})

# 	def check_sal_struct(self, joining_date, relieving_date):
# 		cond = """and sa.employee=%(employee)s and (sa.from_date <= %(start_date)s or
# 				sa.from_date <= %(end_date)s or sa.from_date <= %(joining_date)s)"""
# 		if self.payroll_frequency:
# 			cond += """and ss.payroll_frequency = '%(payroll_frequency)s'""" % {
# 				"payroll_frequency": self.payroll_frequency
# 			}

# 		st_name = frappe.db.sql(
# 			"""
# 			select sa.salary_structure
# 			from `tabSalary Structure Assignment` sa join `tabSalary Structure` ss
# 			where sa.salary_structure=ss.name
# 				and sa.docstatus = 1 and ss.docstatus = 1 and ss.is_active ='Yes' %s
# 			order by sa.from_date desc
# 			limit 1
# 		"""
# 			% cond,
# 			{
# 				"employee": self.employee,
# 				"start_date": self.start_date,
# 				"end_date": self.end_date,
# 				"joining_date": joining_date,
# 			},
# 		)

# 		if st_name:
# 			self.salary_structure = st_name[0][0]
# 			return self.salary_structure

# 		else:
# 			self.salary_structure = None
# 			frappe.msgprint(
# 				_("No active or default Salary Structure found for employee {0} for the given dates").format(
# 					self.employee
# 				),
# 				title=_("Salary Structure Missing"),
# 			)

# 	def pull_sal_struct(self):
# 		from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip

# 		if self.salary_slip_based_on_timesheet:
# 			self.salary_structure = self._salary_structure_doc.name
# 			self.hour_rate = self._salary_structure_doc.hour_rate
# 			self.base_hour_rate = flt(self.hour_rate) * flt(self.exchange_rate)
# 			self.total_working_hours = sum([d.working_hours or 0.0 for d in self.timesheets]) or 0.0
# 			wages_amount = self.hour_rate * self.total_working_hours

# 			self.add_earning_for_hourly_wages(
# 				self, self._salary_structure_doc.salary_component, wages_amount
# 			)

# 		make_salary_slip(self._salary_structure_doc.name, self)

# 	def get_working_days_details(
# 		self, joining_date=None, relieving_date=None, lwp=None, for_preview=0
# 	):
# 		payroll_based_on = frappe.db.get_value("Payroll Settings", None, "payroll_based_on")
# 		include_holidays_in_total_working_days = frappe.db.get_single_value(
# 			"Payroll Settings", "include_holidays_in_total_working_days"
# 		)

# 		working_days = date_diff(self.end_date, self.start_date) + 1
# 		if for_preview:
# 			self.total_working_days = working_days
# 			self.payment_days = working_days
# 			return

# 		holidays = self.get_holidays_for_employee(self.start_date, self.end_date)

# 		if not cint(include_holidays_in_total_working_days):
# 			working_days -= len(holidays)
# 			if working_days < 0:
# 				frappe.throw(_("There are more holidays than working days this month."))

# 		if not payroll_based_on:
# 			frappe.throw(_("Please set Payroll based on in Payroll settings"))

# 		if payroll_based_on == "Attendance":
# 			actual_lwp, absent = self.calculate_lwp_ppl_and_absent_days_based_on_attendance(holidays)
# 			self.absent_days = absent
# 		else:
# 			actual_lwp = self.calculate_lwp_or_ppl_based_on_leave_application(holidays, working_days)

# 		if not lwp:
# 			lwp = actual_lwp
# 		elif lwp != actual_lwp:
# 			frappe.msgprint(
# 				_("Leave Without Pay does not match with approved {} records").format(payroll_based_on)
# 			)

# 		self.leave_without_pay = lwp
# 		self.total_working_days = working_days

# 		payment_days = self.get_payment_days(
# 			joining_date, relieving_date, include_holidays_in_total_working_days
# 		)

# 		if flt(payment_days) > flt(lwp):
# 			self.payment_days = flt(payment_days) - flt(lwp)

# 			if payroll_based_on == "Attendance":
# 				self.payment_days -= flt(absent)

# 			consider_unmarked_attendance_as = (
# 				frappe.db.get_value("Payroll Settings", None, "consider_unmarked_attendance_as") or "Present"
# 			)

# 			if payroll_based_on == "Attendance" and consider_unmarked_attendance_as == "Absent":
# 				unmarked_days = self.get_unmarked_days(include_holidays_in_total_working_days)
# 				self.absent_days += unmarked_days  # will be treated as absent
# 				self.payment_days -= unmarked_days
# 		else:
# 			self.payment_days = 0

# 	def get_unmarked_days(self, include_holidays_in_total_working_days):
# 		unmarked_days = self.total_working_days
# 		joining_date, relieving_date = frappe.get_cached_value(
# 			"Employee", self.employee, ["date_of_joining", "relieving_date"]
# 		)
# 		start_date = self.start_date
# 		end_date = self.end_date

# 		if joining_date and (getdate(self.start_date) < joining_date <= getdate(self.end_date)):
# 			start_date = joining_date
# 			unmarked_days = self.get_unmarked_days_based_on_doj_or_relieving(
# 				unmarked_days,
# 				include_holidays_in_total_working_days,
# 				self.start_date,
# 				add_days(joining_date, -1),
# 			)

# 		if relieving_date and (getdate(self.start_date) <= relieving_date < getdate(self.end_date)):
# 			end_date = relieving_date
# 			unmarked_days = self.get_unmarked_days_based_on_doj_or_relieving(
# 				unmarked_days,
# 				include_holidays_in_total_working_days,
# 				add_days(relieving_date, 1),
# 				self.end_date,
# 			)

# 		# exclude days for which attendance has been marked
# 		unmarked_days -= frappe.get_all(
# 			"Attendance",
# 			filters={
# 				"attendance_date": ["between", [start_date, end_date]],
# 				"employee": self.employee,
# 				"docstatus": 1,
# 			},
# 			fields=["COUNT(*) as marked_days"],
# 		)[0].marked_days

# 		return unmarked_days

# 	def get_unmarked_days_based_on_doj_or_relieving(
# 		self, unmarked_days, include_holidays_in_total_working_days, start_date, end_date
# 	):
# 		"""
# 		Exclude days before DOJ or after
# 		Relieving Date from unmarked days
# 		"""
# 		from erpnext.setup.doctype.employee.employee import is_holiday

# 		if include_holidays_in_total_working_days:
# 			unmarked_days -= date_diff(end_date, start_date) + 1
# 		else:
# 			# exclude only if not holidays
# 			for days in range(date_diff(end_date, start_date) + 1):
# 				date = add_days(end_date, -days)
# 				if not is_holiday(self.employee, date):
# 					unmarked_days -= 1

# 		return unmarked_days

# 	def get_payment_days(self, joining_date, relieving_date, include_holidays_in_total_working_days):
# 		if not joining_date:
# 			joining_date, relieving_date = frappe.get_cached_value(
# 				"Employee", self.employee, ["date_of_joining", "relieving_date"]
# 			)

# 		start_date = getdate(self.start_date)
# 		if joining_date:
# 			if getdate(self.start_date) <= joining_date <= getdate(self.end_date):
# 				start_date = joining_date
# 			elif joining_date > getdate(self.end_date):
# 				return

# 		end_date = getdate(self.end_date)
# 		if relieving_date:
# 			if getdate(self.start_date) <= relieving_date <= getdate(self.end_date):
# 				end_date = relieving_date
# 			elif relieving_date < getdate(self.start_date):
# 				frappe.throw(_("Employee relieved on {0} must be set as 'Left'").format(relieving_date))

# 		payment_days = date_diff(end_date, start_date) + 1

# 		if not cint(include_holidays_in_total_working_days):
# 			holidays = self.get_holidays_for_employee(start_date, end_date)
# 			payment_days -= len(holidays)

# 		return payment_days

# 	def get_holidays_for_employee(self, start_date, end_date):
# 		return get_holiday_dates_for_employee(self.employee, start_date, end_date)

# 	def calculate_lwp_or_ppl_based_on_leave_application(self, holidays, working_days):
# 		lwp = 0
# 		holidays = "','".join(holidays)
# 		daily_wages_fraction_for_half_day = (
# 			flt(frappe.db.get_value("Payroll Settings", None, "daily_wages_fraction_for_half_day")) or 0.5
# 		)

# 		for d in range(working_days):
# 			date = add_days(cstr(getdate(self.start_date)), d)
# 			leave = get_lwp_or_ppl_for_date(date, self.employee, holidays)

# 			if leave:
# 				equivalent_lwp_count = 0
# 				is_half_day_leave = cint(leave[0].is_half_day)
# 				is_partially_paid_leave = cint(leave[0].is_ppl)
# 				fraction_of_daily_salary_per_leave = flt(leave[0].fraction_of_daily_salary_per_leave)

# 				equivalent_lwp_count = (1 - daily_wages_fraction_for_half_day) if is_half_day_leave else 1

# 				if is_partially_paid_leave:
# 					equivalent_lwp_count *= (
# 						fraction_of_daily_salary_per_leave if fraction_of_daily_salary_per_leave else 1
# 					)

# 				lwp += equivalent_lwp_count

# 		return lwp

# 	def calculate_lwp_ppl_and_absent_days_based_on_attendance(self, holidays):
# 		lwp = 0
# 		absent = 0

# 		daily_wages_fraction_for_half_day = (
# 			flt(frappe.db.get_value("Payroll Settings", None, "daily_wages_fraction_for_half_day")) or 0.5
# 		)

# 		leave_types = frappe.get_all(
# 			"Leave Type",
# 			or_filters=[["is_ppl", "=", 1], ["is_lwp", "=", 1]],
# 			fields=["name", "is_lwp", "is_ppl", "fraction_of_daily_salary_per_leave", "include_holiday"],
# 		)

# 		leave_type_map = {}
# 		for leave_type in leave_types:
# 			leave_type_map[leave_type.name] = leave_type

# 		attendances = frappe.db.sql(
# 			"""
# 			SELECT attendance_date, status, leave_type
# 			FROM `tabAttendance`
# 			WHERE
# 				status in ('Absent', 'Half Day', 'On leave')
# 				AND employee = %s
# 				AND docstatus = 1
# 				AND attendance_date between %s and %s
# 		""",
# 			values=(self.employee, self.start_date, self.end_date),
# 			as_dict=1,
# 		)

# 		for d in attendances:
# 			if (
# 				d.status in ("Half Day", "On Leave")
# 				and d.leave_type
# 				and d.leave_type not in leave_type_map.keys()
# 			):
# 				continue

# 			if formatdate(d.attendance_date, "yyyy-mm-dd") in holidays:
# 				if d.status == "Absent" or (
# 					d.leave_type
# 					and d.leave_type in leave_type_map.keys()
# 					and not leave_type_map[d.leave_type]["include_holiday"]
# 				):
# 					continue

# 			if d.leave_type:
# 				fraction_of_daily_salary_per_leave = leave_type_map[d.leave_type][
# 					"fraction_of_daily_salary_per_leave"
# 				]

# 			if d.status == "Half Day":
# 				equivalent_lwp = 1 - daily_wages_fraction_for_half_day

# 				if d.leave_type in leave_type_map.keys() and leave_type_map[d.leave_type]["is_ppl"]:
# 					equivalent_lwp *= (
# 						fraction_of_daily_salary_per_leave if fraction_of_daily_salary_per_leave else 1
# 					)
# 				lwp += equivalent_lwp
# 			elif d.status == "On Leave" and d.leave_type and d.leave_type in leave_type_map.keys():
# 				equivalent_lwp = 1
# 				if leave_type_map[d.leave_type]["is_ppl"]:
# 					equivalent_lwp *= (
# 						fraction_of_daily_salary_per_leave if fraction_of_daily_salary_per_leave else 1
# 					)
# 				lwp += equivalent_lwp
# 			elif d.status == "Absent":
# 				absent += 1
# 		return lwp, absent

# 	def add_earning_for_hourly_wages(self, doc, salary_component, amount):
# 		row_exists = False
# 		for row in doc.earnings:
# 			if row.salary_component == salary_component:
# 				row.amount = amount
# 				row_exists = True
# 				break

# 		if not row_exists:
# 			wages_row = {
# 				"salary_component": salary_component,
# 				"abbr": frappe.db.get_value("Salary Component", salary_component, "salary_component_abbr"),
# 				"amount": self.hour_rate * self.total_working_hours,
# 				"default_amount": 0.0,
# 				"additional_amount": 0.0,
# 			}
# 			doc.append("earnings", wages_row)

# 	def calculate_net_pay(self):
# 		if self.salary_structure:
# 			self.calculate_component_amounts("earnings")
# 		self.gross_pay = self.get_component_totals("earnings", depends_on_payment_days=1)
# 		self.base_gross_pay = flt(
# 			flt(self.gross_pay) * flt(self.exchange_rate), self.precision("base_gross_pay")
# 		)

# 		if self.salary_structure:
# 			self.calculate_component_amounts("deductions")

# 		self.set_loan_repayment()
# 		self.set_precision_for_component_amounts()
# 		self.set_net_pay()

# 	def set_net_pay(self):
# 		self.total_deduction = self.get_component_totals("deductions")
# 		self.base_total_deduction = flt(
# 			flt(self.total_deduction) * flt(self.exchange_rate), self.precision("base_total_deduction")
# 		)
# 		self.net_pay = flt(self.gross_pay) - (flt(self.total_deduction) + flt(self.total_loan_repayment))
# 		self.rounded_total = rounded(self.net_pay)
# 		self.base_net_pay = flt(
# 			flt(self.net_pay) * flt(self.exchange_rate), self.precision("base_net_pay")
# 		)
# 		self.base_rounded_total = flt(rounded(self.base_net_pay), self.precision("base_net_pay"))
# 		if self.hour_rate:
# 			self.base_hour_rate = flt(
# 				flt(self.hour_rate) * flt(self.exchange_rate), self.precision("base_hour_rate")
# 			)
# 		self.set_net_total_in_words()

# 	def calculate_component_amounts(self, component_type):
# 		if not getattr(self, "_salary_structure_doc", None):
# 			self._salary_structure_doc = frappe.get_doc("Salary Structure", self.salary_structure)

# 		payroll_period = get_payroll_period(self.start_date, self.end_date, self.company)

# 		self.add_structure_components(component_type)
# 		self.add_additional_salary_components(component_type)
# 		if component_type == "earnings":
# 			self.add_employee_benefits(payroll_period)
# 		else:
# 			self.add_tax_components(payroll_period)

# 	def add_structure_components(self, component_type):
# 		data, default_data = self.get_data_for_eval()
# 		timesheet_component = frappe.db.get_value(
# 			"Salary Structure", self.salary_structure, "salary_component"
# 		)

# 		for struct_row in self._salary_structure_doc.get(component_type):
# 			if self.salary_slip_based_on_timesheet and struct_row.salary_component == timesheet_component:
# 				continue

# 			amount = self.eval_condition_and_formula(struct_row, data)
# 			if (
# 				amount or (struct_row.amount_based_on_formula and amount is not None)
# 			) and struct_row.statistical_component == 0:
# 				default_amount = self.eval_condition_and_formula(struct_row, default_data)
# 				self.update_component_row(
# 					struct_row, amount, component_type, data=data, default_amount=default_amount
# 				)

# 	def get_data_for_eval(self):
# 		"""Returns data for evaluating formula"""
# 		data = frappe._dict()
# 		employee = frappe.get_doc("Employee", self.employee).as_dict()

# 		start_date = getdate(self.start_date)
# 		date_to_validate = (
# 			employee.date_of_joining if employee.date_of_joining > start_date else start_date
# 		)

# 		salary_structure_assignment = frappe.get_value(
# 			"Salary Structure Assignment",
# 			{
# 				"employee": self.employee,
# 				"salary_structure": self.salary_structure,
# 				"from_date": ("<=", date_to_validate),
# 				"docstatus": 1,
# 			},
# 			"*",
# 			order_by="from_date desc",
# 			as_dict=True,
# 		)

# 		if not salary_structure_assignment:
# 			frappe.throw(
# 				_(
# 					"Please assign a Salary Structure for Employee {0} " "applicable from or before {1} first"
# 				).format(
# 					frappe.bold(self.employee_name),
# 					frappe.bold(formatdate(date_to_validate)),
# 				)
# 			)

# 		data.update(salary_structure_assignment)
# 		data.update(employee)
# 		data.update(self.as_dict())

# 		# set values for components
# 		salary_components = frappe.get_all("Salary Component", fields=["salary_component_abbr"])
# 		for sc in salary_components:
# 			data.setdefault(sc.salary_component_abbr, 0)

# 		# shallow copy of data to store default amounts (without payment days) for tax calculation
# 		default_data = data.copy()

# 		for key in ("earnings", "deductions"):
# 			for d in self.get(key):
# 				default_data[d.abbr] = d.default_amount
# 				data[d.abbr] = d.amount

# 		return data, default_data

# 	def eval_condition_and_formula(self, d, data):
# 		try:
# 			condition = d.condition.strip().replace("\n", " ") if d.condition else None
# 			if condition:
# 				if not frappe.safe_eval(condition, self.whitelisted_globals, data):
# 					return None
# 			amount = d.amount
# 			if d.amount_based_on_formula:
# 				formula = d.formula.strip().replace("\n", " ") if d.formula else None
# 				if formula:
# 					amount = flt(frappe.safe_eval(formula, self.whitelisted_globals, data), d.precision("amount"))
# 			if amount:
# 				data[d.abbr] = amount

# 			return amount

# 		except NameError as err:
# 			frappe.throw(
# 				_("{0} <br> This error can be due to missing or deleted field.").format(err),
# 				title=_("Name error"),
# 			)
# 		except SyntaxError as err:
# 			frappe.throw(_("Syntax error in formula or condition: {0}").format(err))
# 		except Exception as e:
# 			frappe.throw(_("Error in formula or condition: {0}").format(e))
# 			raise

# 	def add_employee_benefits(self, payroll_period):
# 		for struct_row in self._salary_structure_doc.get("earnings"):
# 			if struct_row.is_flexible_benefit == 1:
# 				if (
# 					frappe.db.get_value(
# 						"Salary Component", struct_row.salary_component, "pay_against_benefit_claim"
# 					)
# 					!= 1
# 				):
# 					benefit_component_amount = get_benefit_component_amount(
# 						self.employee,
# 						self.start_date,
# 						self.end_date,
# 						struct_row.salary_component,
# 						self._salary_structure_doc,
# 						self.payroll_frequency,
# 						payroll_period,
# 					)
# 					if benefit_component_amount:
# 						self.update_component_row(struct_row, benefit_component_amount, "earnings")
# 				else:
# 					benefit_claim_amount = get_benefit_claim_amount(
# 						self.employee, self.start_date, self.end_date, struct_row.salary_component
# 					)
# 					if benefit_claim_amount:
# 						self.update_component_row(struct_row, benefit_claim_amount, "earnings")

# 		self.adjust_benefits_in_last_payroll_period(payroll_period)

# 	def adjust_benefits_in_last_payroll_period(self, payroll_period):
# 		if payroll_period:
# 			if getdate(payroll_period.end_date) <= getdate(self.end_date):
# 				last_benefits = get_last_payroll_period_benefits(
# 					self.employee, self.start_date, self.end_date, payroll_period, self._salary_structure_doc
# 				)
# 				if last_benefits:
# 					for last_benefit in last_benefits:
# 						last_benefit = frappe._dict(last_benefit)
# 						amount = last_benefit.amount
# 						self.update_component_row(frappe._dict(last_benefit.struct_row), amount, "earnings")

# 	def add_additional_salary_components(self, component_type):
# 		additional_salaries = get_additional_salaries(
# 			self.employee, self.start_date, self.end_date, component_type
# 		)

# 		for additional_salary in additional_salaries:
# 			self.update_component_row(
# 				get_salary_component_data(additional_salary.component),
# 				additional_salary.amount,
# 				component_type,
# 				additional_salary,
# 				is_recurring=additional_salary.is_recurring,
# 			)

# 	def add_tax_components(self, payroll_period):
# 		# Calculate variable_based_on_taxable_salary after all components updated in salary slip
# 		tax_components, other_deduction_components = [], []
# 		for d in self._salary_structure_doc.get("deductions"):
# 			if d.variable_based_on_taxable_salary == 1 and not d.formula and not flt(d.amount):
# 				tax_components.append(d.salary_component)
# 			else:
# 				other_deduction_components.append(d.salary_component)

# 		if not tax_components:
# 			tax_components = [
# 				d.name
# 				for d in frappe.get_all("Salary Component", filters={"variable_based_on_taxable_salary": 1})
# 				if d.name not in other_deduction_components
# 			]

# 		for d in tax_components:
# 			tax_amount = self.calculate_variable_based_on_taxable_salary(d, payroll_period)
# 			tax_row = get_salary_component_data(d)
# 			self.update_component_row(tax_row, tax_amount, "deductions")

# 	def update_component_row(
# 		self,
# 		component_data,
# 		amount,
# 		component_type,
# 		additional_salary=None,
# 		is_recurring=0,
# 		data=None,
# 		default_amount=None,
# 	):
# 		component_row = None
# 		for d in self.get(component_type):
# 			if d.salary_component != component_data.salary_component:
# 				continue

# 			if (not d.additional_salary and (not additional_salary or additional_salary.overwrite)) or (
# 				additional_salary and additional_salary.name == d.additional_salary
# 			):
# 				component_row = d
# 				break

# 		if additional_salary and additional_salary.overwrite:
# 			# Additional Salary with overwrite checked, remove default rows of same component
# 			self.set(
# 				component_type,
# 				[
# 					d
# 					for d in self.get(component_type)
# 					if d.salary_component != component_data.salary_component
# 					or (d.additional_salary and additional_salary.name != d.additional_salary)
# 					or d == component_row
# 				],
# 			)

# 		if not component_row:
# 			if not amount:
# 				return

# 			component_row = self.append(component_type)
# 			for attr in (
# 				"depends_on_payment_days",
# 				"salary_component",
# 				"abbr",
# 				"do_not_include_in_total",
# 				"is_tax_applicable",
# 				"is_flexible_benefit",
# 				"variable_based_on_taxable_salary",
# 				"exempted_from_income_tax",
# 			):
# 				component_row.set(attr, component_data.get(attr))

# 		if additional_salary:
# 			if additional_salary.overwrite:
# 				component_row.additional_amount = flt(
# 					flt(amount) - flt(component_row.get("default_amount", 0)),
# 					component_row.precision("additional_amount"),
# 				)
# 			else:
# 				component_row.default_amount = 0
# 				component_row.additional_amount = amount

# 			component_row.is_recurring_additional_salary = is_recurring
# 			component_row.additional_salary = additional_salary.name
# 			component_row.deduct_full_tax_on_selected_payroll_date = (
# 				additional_salary.deduct_full_tax_on_selected_payroll_date
# 			)
# 		else:
# 			component_row.default_amount = default_amount or amount
# 			component_row.additional_amount = 0
# 			component_row.deduct_full_tax_on_selected_payroll_date = (
# 				component_data.deduct_full_tax_on_selected_payroll_date
# 			)

# 		component_row.amount = amount

# 		self.update_component_amount_based_on_payment_days(component_row)

# 		if data:
# 			data[component_row.abbr] = component_row.amount

# 	def update_component_amount_based_on_payment_days(self, component_row):
# 		joining_date, relieving_date = self.get_joining_and_relieving_dates()
# 		component_row.amount = self.get_amount_based_on_payment_days(
# 			component_row, joining_date, relieving_date
# 		)[0]

# 		# remove 0 valued components that have been updated later
# 		if component_row.amount == 0:
# 			self.remove(component_row)

# 	def set_precision_for_component_amounts(self):
# 		for component_type in ("earnings", "deductions"):
# 			for component_row in self.get(component_type):
# 				component_row.amount = flt(component_row.amount, component_row.precision("amount"))

# 	def calculate_variable_based_on_taxable_salary(self, tax_component, payroll_period):
# 		if not payroll_period:
# 			frappe.msgprint(
# 				_("Start and end dates not in a valid Payroll Period, cannot calculate {0}.").format(
# 					tax_component
# 				)
# 			)
# 			return

# 		# Deduct taxes forcefully for unsubmitted tax exemption proof and unclaimed benefits in the last period
# 		if payroll_period.end_date <= getdate(self.end_date):
# 			self.deduct_tax_for_unsubmitted_tax_exemption_proof = 1
# 			self.deduct_tax_for_unclaimed_employee_benefits = 1

# 		return self.calculate_variable_tax(payroll_period, tax_component)

# 	def calculate_variable_tax(self, payroll_period, tax_component):
# 		# get Tax slab from salary structure assignment for the employee and payroll period
# 		tax_slab = self.get_income_tax_slabs(payroll_period)

# 		# get remaining numbers of sub-period (period for which one salary is processed)
# 		remaining_sub_periods = get_period_factor(
# 			self.employee, self.start_date, self.end_date, self.payroll_frequency, payroll_period
# 		)[1]
# 		# get taxable_earnings, paid_taxes for previous period
# 		previous_taxable_earnings = self.get_taxable_earnings_for_prev_period(
# 			payroll_period.start_date, self.start_date, tax_slab.allow_tax_exemption
# 		)
# 		previous_total_paid_taxes = self.get_tax_paid_in_period(
# 			payroll_period.start_date, self.start_date, tax_component
# 		)

# 		# get taxable_earnings for current period (all days)
# 		current_taxable_earnings = self.get_taxable_earnings(
# 			tax_slab.allow_tax_exemption, payroll_period=payroll_period
# 		)
# 		future_structured_taxable_earnings = current_taxable_earnings.taxable_earnings * (
# 			math.ceil(remaining_sub_periods) - 1
# 		)

# 		# get taxable_earnings, addition_earnings for current actual payment days
# 		current_taxable_earnings_for_payment_days = self.get_taxable_earnings(
# 			tax_slab.allow_tax_exemption, based_on_payment_days=1, payroll_period=payroll_period
# 		)
# 		current_structured_taxable_earnings = current_taxable_earnings_for_payment_days.taxable_earnings
# 		current_additional_earnings = current_taxable_earnings_for_payment_days.additional_income
# 		current_additional_earnings_with_full_tax = (
# 			current_taxable_earnings_for_payment_days.additional_income_with_full_tax
# 		)

# 		# Get taxable unclaimed benefits
# 		unclaimed_taxable_benefits = 0
# 		if self.deduct_tax_for_unclaimed_employee_benefits:
# 			unclaimed_taxable_benefits = self.calculate_unclaimed_taxable_benefits(payroll_period)
# 			unclaimed_taxable_benefits += current_taxable_earnings_for_payment_days.flexi_benefits

# 		# Total exemption amount based on tax exemption declaration
# 		total_exemption_amount = self.get_total_exemption_amount(payroll_period, tax_slab)

# 		# Employee Other Incomes
# 		other_incomes = self.get_income_form_other_sources(payroll_period) or 0.0

# 		# Total taxable earnings including additional and other incomes
# 		total_taxable_earnings = (
# 			previous_taxable_earnings
# 			+ current_structured_taxable_earnings
# 			+ future_structured_taxable_earnings
# 			+ current_additional_earnings
# 			+ other_incomes
# 			+ unclaimed_taxable_benefits
# 			- total_exemption_amount
# 		)

# 		# Total taxable earnings without additional earnings with full tax
# 		total_taxable_earnings_without_full_tax_addl_components = (
# 			total_taxable_earnings - current_additional_earnings_with_full_tax
# 		)

# 		# Structured tax amount
# 		eval_locals, default_data = self.get_data_for_eval()
# 		total_structured_tax_amount = calculate_tax_by_tax_slab(
# 			total_taxable_earnings_without_full_tax_addl_components,
# 			tax_slab,
# 			self.whitelisted_globals,
# 			eval_locals,
# 		)
# 		current_structured_tax_amount = (
# 			total_structured_tax_amount - previous_total_paid_taxes
# 		) / remaining_sub_periods

# 		# Total taxable earnings with additional earnings with full tax
# 		full_tax_on_additional_earnings = 0.0
# 		if current_additional_earnings_with_full_tax:
# 			total_tax_amount = calculate_tax_by_tax_slab(
# 				total_taxable_earnings, tax_slab, self.whitelisted_globals, eval_locals
# 			)
# 			full_tax_on_additional_earnings = total_tax_amount - total_structured_tax_amount

# 		current_tax_amount = current_structured_tax_amount + full_tax_on_additional_earnings
# 		if flt(current_tax_amount) < 0:
# 			current_tax_amount = 0

# 		return current_tax_amount

# 	def get_income_tax_slabs(self, payroll_period):
# 		income_tax_slab, ss_assignment_name = frappe.db.get_value(
# 			"Salary Structure Assignment",
# 			{"employee": self.employee, "salary_structure": self.salary_structure, "docstatus": 1},
# 			["income_tax_slab", "name"],
# 		)

# 		if not income_tax_slab:
# 			frappe.throw(
# 				_("Income Tax Slab not set in Salary Structure Assignment: {0}").format(ss_assignment_name)
# 			)

# 		income_tax_slab_doc = frappe.get_doc("Income Tax Slab", income_tax_slab)
# 		if income_tax_slab_doc.disabled:
# 			frappe.throw(_("Income Tax Slab: {0} is disabled").format(income_tax_slab))

# 		if getdate(income_tax_slab_doc.effective_from) > getdate(payroll_period.start_date):
# 			frappe.throw(
# 				_("Income Tax Slab must be effective on or before Payroll Period Start Date: {0}").format(
# 					payroll_period.start_date
# 				)
# 			)

# 		return income_tax_slab_doc

# 	def get_taxable_earnings_for_prev_period(self, start_date, end_date, allow_tax_exemption=False):
# 		taxable_earnings = frappe.db.sql(
# 			"""
# 			select sum(sd.amount)
# 			from
# 				`tabSalary Detail` sd join `tabSalary Slip` ss on sd.parent=ss.name
# 			where
# 				sd.parentfield='earnings'
# 				and sd.is_tax_applicable=1
# 				and is_flexible_benefit=0
# 				and ss.docstatus=1
# 				and ss.employee=%(employee)s
# 				and ss.start_date between %(from_date)s and %(to_date)s
# 				and ss.end_date between %(from_date)s and %(to_date)s
# 			""",
# 			{"employee": self.employee, "from_date": start_date, "to_date": end_date},
# 		)
# 		taxable_earnings = flt(taxable_earnings[0][0]) if taxable_earnings else 0

# 		exempted_amount = 0
# 		if allow_tax_exemption:
# 			exempted_amount = frappe.db.sql(
# 				"""
# 				select sum(sd.amount)
# 				from
# 					`tabSalary Detail` sd join `tabSalary Slip` ss on sd.parent=ss.name
# 				where
# 					sd.parentfield='deductions'
# 					and sd.exempted_from_income_tax=1
# 					and is_flexible_benefit=0
# 					and ss.docstatus=1
# 					and ss.employee=%(employee)s
# 					and ss.start_date between %(from_date)s and %(to_date)s
# 					and ss.end_date between %(from_date)s and %(to_date)s
# 				""",
# 				{"employee": self.employee, "from_date": start_date, "to_date": end_date},
# 			)
# 			exempted_amount = flt(exempted_amount[0][0]) if exempted_amount else 0

# 		return taxable_earnings - exempted_amount

# 	def get_tax_paid_in_period(self, start_date, end_date, tax_component):
# 		# find total_tax_paid, tax paid for benefit, additional_salary
# 		total_tax_paid = flt(
# 			frappe.db.sql(
# 				"""
# 			select
# 				sum(sd.amount)
# 			from
# 				`tabSalary Detail` sd join `tabSalary Slip` ss on sd.parent=ss.name
# 			where
# 				sd.parentfield='deductions'
# 				and sd.salary_component=%(salary_component)s
# 				and sd.variable_based_on_taxable_salary=1
# 				and ss.docstatus=1
# 				and ss.employee=%(employee)s
# 				and ss.start_date between %(from_date)s and %(to_date)s
# 				and ss.end_date between %(from_date)s and %(to_date)s
# 		""",
# 				{
# 					"salary_component": tax_component,
# 					"employee": self.employee,
# 					"from_date": start_date,
# 					"to_date": end_date,
# 				},
# 			)[0][0]
# 		)

# 		return total_tax_paid

# 	def get_taxable_earnings(
# 		self, allow_tax_exemption=False, based_on_payment_days=0, payroll_period=None
# 	):
# 		joining_date, relieving_date = self.get_joining_and_relieving_dates()

# 		taxable_earnings = 0
# 		additional_income = 0
# 		additional_income_with_full_tax = 0
# 		flexi_benefits = 0

# 		for earning in self.earnings:
# 			if based_on_payment_days:
# 				amount, additional_amount = self.get_amount_based_on_payment_days(
# 					earning, joining_date, relieving_date
# 				)
# 			else:
# 				if earning.additional_amount:
# 					amount, additional_amount = earning.amount, earning.additional_amount
# 				else:
# 					amount, additional_amount = earning.default_amount, earning.additional_amount

# 			if earning.is_tax_applicable:
# 				if earning.is_flexible_benefit:
# 					flexi_benefits += amount
# 				else:
# 					taxable_earnings += amount - additional_amount
# 					additional_income += additional_amount

# 					# Get additional amount based on future recurring additional salary
# 					if additional_amount and earning.is_recurring_additional_salary:
# 						additional_income += self.get_future_recurring_additional_amount(
# 							earning.additional_salary, earning.additional_amount, payroll_period
# 						)  # Used earning.additional_amount to consider the amount for the full month

# 					if earning.deduct_full_tax_on_selected_payroll_date:
# 						additional_income_with_full_tax += additional_amount

# 		if allow_tax_exemption:
# 			for ded in self.deductions:
# 				if ded.exempted_from_income_tax:
# 					amount, additional_amount = ded.amount, ded.additional_amount
# 					if based_on_payment_days:
# 						amount, additional_amount = self.get_amount_based_on_payment_days(
# 							ded, joining_date, relieving_date
# 						)

# 					taxable_earnings -= flt(amount - additional_amount)
# 					additional_income -= additional_amount

# 					if additional_amount and ded.is_recurring_additional_salary:
# 						additional_income -= self.get_future_recurring_additional_amount(
# 							ded.additional_salary, ded.additional_amount, payroll_period
# 						)  # Used ded.additional_amount to consider the amount for the full month

# 		return frappe._dict(
# 			{
# 				"taxable_earnings": taxable_earnings,
# 				"additional_income": additional_income,
# 				"additional_income_with_full_tax": additional_income_with_full_tax,
# 				"flexi_benefits": flexi_benefits,
# 			}
# 		)

# 	def get_future_recurring_additional_amount(
# 		self, additional_salary, monthly_additional_amount, payroll_period
# 	):
# 		future_recurring_additional_amount = 0
# 		to_date = frappe.db.get_value("Additional Salary", additional_salary, "to_date")

# 		# future month count excluding current
# 		from_date, to_date = getdate(self.start_date), getdate(to_date)

# 		# If recurring period end date is beyond the payroll period,
# 		# last day of payroll period should be considered for recurring period calculation
# 		if getdate(to_date) > getdate(payroll_period.end_date):
# 			to_date = getdate(payroll_period.end_date)

# 		future_recurring_period = ((to_date.year - from_date.year) * 12) + (
# 			to_date.month - from_date.month
# 		)

# 		if future_recurring_period > 0:
# 			future_recurring_additional_amount = (
# 				monthly_additional_amount * future_recurring_period
# 			)  # Used earning.additional_amount to consider the amount for the full month
# 		return future_recurring_additional_amount

# 	def get_amount_based_on_payment_days(self, row, joining_date, relieving_date):
# 		amount, additional_amount = row.amount, row.additional_amount
# 		timesheet_component = frappe.db.get_value(
# 			"Salary Structure", self.salary_structure, "salary_component"
# 		)

# 		if (
# 			self.salary_structure
# 			and cint(row.depends_on_payment_days)
# 			and cint(self.total_working_days)
# 			and not (
# 				row.additional_salary and row.default_amount
# 			)  # to identify overwritten additional salary
# 			and (
# 				row.salary_component != timesheet_component
# 				or getdate(self.start_date) < joining_date
# 				or (relieving_date and getdate(self.end_date) > relieving_date)
# 			)
# 		):
# 			additional_amount = flt(
# 				(flt(row.additional_amount) * flt(self.payment_days) / cint(self.total_working_days)),
# 				row.precision("additional_amount"),
# 			)
# 			amount = (
# 				flt(
# 					(flt(row.default_amount) * flt(self.payment_days) / cint(self.total_working_days)),
# 					row.precision("amount"),
# 				)
# 				+ additional_amount
# 			)

# 		elif (
# 			not self.payment_days
# 			and row.salary_component != timesheet_component
# 			and cint(row.depends_on_payment_days)
# 		):
# 			amount, additional_amount = 0, 0
# 		elif not row.amount:
# 			amount = flt(row.default_amount) + flt(row.additional_amount)

# 		# apply rounding
# 		if frappe.get_cached_value(
# 			"Salary Component", row.salary_component, "round_to_the_nearest_integer"
# 		):
# 			amount, additional_amount = rounded(amount or 0), rounded(additional_amount or 0)

# 		return amount, additional_amount

# 	def calculate_unclaimed_taxable_benefits(self, payroll_period):
# 		# get total sum of benefits paid
# 		total_benefits_paid = flt(
# 			frappe.db.sql(
# 				"""
# 			select sum(sd.amount)
# 			from `tabSalary Detail` sd join `tabSalary Slip` ss on sd.parent=ss.name
# 			where
# 				sd.parentfield='earnings'
# 				and sd.is_tax_applicable=1
# 				and is_flexible_benefit=1
# 				and ss.docstatus=1
# 				and ss.employee=%(employee)s
# 				and ss.start_date between %(start_date)s and %(end_date)s
# 				and ss.end_date between %(start_date)s and %(end_date)s
# 		""",
# 				{
# 					"employee": self.employee,
# 					"start_date": payroll_period.start_date,
# 					"end_date": self.start_date,
# 				},
# 			)[0][0]
# 		)

# 		# get total benefits claimed
# 		total_benefits_claimed = flt(
# 			frappe.db.sql(
# 				"""
# 			select sum(claimed_amount)
# 			from `tabEmployee Benefit Claim`
# 			where
# 				docstatus=1
# 				and employee=%s
# 				and claim_date between %s and %s
# 		""",
# 				(self.employee, payroll_period.start_date, self.end_date),
# 			)[0][0]
# 		)

# 		return total_benefits_paid - total_benefits_claimed

# 	def get_total_exemption_amount(self, payroll_period, tax_slab):
# 		total_exemption_amount = 0
# 		if tax_slab.allow_tax_exemption:
# 			if self.deduct_tax_for_unsubmitted_tax_exemption_proof:
# 				exemption_proof = frappe.db.get_value(
# 					"Employee Tax Exemption Proof Submission",
# 					{"employee": self.employee, "payroll_period": payroll_period.name, "docstatus": 1},
# 					["exemption_amount"],
# 				)
# 				if exemption_proof:
# 					total_exemption_amount = exemption_proof
# 			else:
# 				declaration = frappe.db.get_value(
# 					"Employee Tax Exemption Declaration",
# 					{"employee": self.employee, "payroll_period": payroll_period.name, "docstatus": 1},
# 					["total_exemption_amount"],
# 				)
# 				if declaration:
# 					total_exemption_amount = declaration

# 			total_exemption_amount += flt(tax_slab.standard_tax_exemption_amount)

# 		return total_exemption_amount

# 	def get_income_form_other_sources(self, payroll_period):
# 		return frappe.get_all(
# 			"Employee Other Income",
# 			filters={
# 				"employee": self.employee,
# 				"payroll_period": payroll_period.name,
# 				"company": self.company,
# 				"docstatus": 1,
# 			},
# 			fields="SUM(amount) as total_amount",
# 		)[0].total_amount

# 	def get_component_totals(self, component_type, depends_on_payment_days=0):
# 		joining_date, relieving_date = frappe.get_cached_value(
# 			"Employee", self.employee, ["date_of_joining", "relieving_date"]
# 		)

# 		total = 0.0
# 		for d in self.get(component_type):
# 			if not d.do_not_include_in_total:
# 				if depends_on_payment_days:
# 					amount = self.get_amount_based_on_payment_days(d, joining_date, relieving_date)[0]
# 				else:
# 					amount = flt(d.amount, d.precision("amount"))
# 				total += amount
# 		return total

# 	def get_joining_and_relieving_dates(self):
# 		joining_date, relieving_date = frappe.get_cached_value(
# 			"Employee", self.employee, ["date_of_joining", "relieving_date"]
# 		)

# 		if not relieving_date:
# 			relieving_date = getdate(self.end_date)

# 		if not joining_date:
# 			frappe.throw(
# 				_("Please set the Date Of Joining for employee {0}").format(frappe.bold(self.employee_name))
# 			)

# 		return joining_date, relieving_date

# 	def set_loan_repayment(self):
# 		self.total_loan_repayment = 0
# 		self.total_interest_amount = 0
# 		self.total_principal_amount = 0

# 		if not self.get("loans"):
# 			for loan in self.get_loan_details():

# 				amounts = calculate_amounts(loan.name, self.posting_date, "Regular Payment")

# 				if amounts["interest_amount"] or amounts["payable_principal_amount"]:
# 					self.append(
# 						"loans",
# 						{
# 							"loan": loan.name,
# 							"total_payment": amounts["interest_amount"] + amounts["payable_principal_amount"],
# 							"interest_amount": amounts["interest_amount"],
# 							"principal_amount": amounts["payable_principal_amount"],
# 							"loan_account": loan.loan_account,
# 							"interest_income_account": loan.interest_income_account,
# 						},
# 					)

# 		for payment in self.get("loans"):
# 			amounts = calculate_amounts(payment.loan, self.posting_date, "Regular Payment")
# 			total_amount = amounts["interest_amount"] + amounts["payable_principal_amount"]
# 			if payment.total_payment > total_amount:
# 				frappe.throw(
# 					_(
# 						"""Row {0}: Paid amount {1} is greater than pending accrued amount {2} against loan {3}"""
# 					).format(
# 						payment.idx,
# 						frappe.bold(payment.total_payment),
# 						frappe.bold(total_amount),
# 						frappe.bold(payment.loan),
# 					)
# 				)

# 			self.total_interest_amount += payment.interest_amount
# 			self.total_principal_amount += payment.principal_amount

# 			self.total_loan_repayment += payment.total_payment

# 	def get_loan_details(self):
# 		loan_details = frappe.get_all(
# 			"Loan",
# 			fields=["name", "interest_income_account", "loan_account", "loan_type", "is_term_loan"],
# 			filters={
# 				"applicant": self.employee,
# 				"docstatus": 1,
# 				"repay_from_salary": 1,
# 				"company": self.company,
# 			},
# 		)

# 		if loan_details:
# 			for loan in loan_details:
# 				if loan.is_term_loan:
# 					process_loan_interest_accrual_for_term_loans(
# 						posting_date=self.posting_date, loan_type=loan.loan_type, loan=loan.name
# 					)

# 		return loan_details

# 	def make_loan_repayment_entry(self):
# 		payroll_payable_account = get_payroll_payable_account(self.company, self.payroll_entry)
# 		for loan in self.loans:
# 			if loan.total_payment:
# 				repayment_entry = create_repayment_entry(
# 					loan.loan,
# 					self.employee,
# 					self.company,
# 					self.posting_date,
# 					loan.loan_type,
# 					"Regular Payment",
# 					loan.interest_amount,
# 					loan.principal_amount,
# 					loan.total_payment,
# 					payroll_payable_account=payroll_payable_account,
# 				)

# 				repayment_entry.save()
# 				repayment_entry.submit()

# 				frappe.db.set_value(
# 					"Salary Slip Loan", loan.name, "loan_repayment_entry", repayment_entry.name
# 				)

# 	def cancel_loan_repayment_entry(self):
# 		for loan in self.loans:
# 			if loan.loan_repayment_entry:
# 				repayment_entry = frappe.get_doc("Loan Repayment", loan.loan_repayment_entry)
# 				repayment_entry.cancel()

# 	def email_salary_slip(self):
# 		receiver = frappe.db.get_value("Employee", self.employee, "prefered_email")
# 		payroll_settings = frappe.get_single("Payroll Settings")
# 		message = "Please see attachment"
# 		password = None
# 		if payroll_settings.encrypt_salary_slips_in_emails:
# 			password = generate_password_for_pdf(payroll_settings.password_policy, self.employee)
# 			message += """<br>Note: Your salary slip is password protected,
# 				the password to unlock the PDF is of the format {0}. """.format(
# 				payroll_settings.password_policy
# 			)

# 		if receiver:
# 			email_args = {
# 				"recipients": [receiver],
# 				"message": _(message),
# 				"subject": "Salary Slip - from {0} to {1}".format(self.start_date, self.end_date),
# 				"attachments": [
# 					frappe.attach_print(self.doctype, self.name, file_name=self.name, password=password)
# 				],
# 				"reference_doctype": self.doctype,
# 				"reference_name": self.name,
# 			}
# 			if not frappe.flags.in_test:
# 				enqueue(method=frappe.sendmail, queue="short", timeout=300, is_async=True, **email_args)
# 			else:
# 				frappe.sendmail(**email_args)
# 		else:
# 			msgprint(_("{0}: Employee email not found, hence email not sent").format(self.employee_name))

# 	def update_status(self, salary_slip=None):
# 		for data in self.timesheets:
# 			if data.time_sheet:
# 				timesheet = frappe.get_doc("Timesheet", data.time_sheet)
# 				timesheet.salary_slip = salary_slip
# 				timesheet.flags.ignore_validate_update_after_submit = True
# 				timesheet.set_status()
# 				timesheet.save()

# 	def set_status(self, status=None):
# 		"""Get and update status"""
# 		if not status:
# 			status = self.get_status()
# 		self.db_set("status", status)

# 	def process_salary_structure(self, for_preview=0):
# 		"""Calculate salary after salary structure details have been updated"""
# 		if not self.salary_slip_based_on_timesheet:
# 			self.get_date_details()
# 		self.pull_emp_details()
# 		self.get_working_days_details(for_preview=for_preview)
# 		self.calculate_net_pay()

# 	def pull_emp_details(self):
# 		emp = frappe.db.get_value(
# 			"Employee", self.employee, ["bank_name", "bank_ac_no", "salary_mode"], as_dict=1
# 		)
# 		if emp:
# 			self.mode_of_payment = emp.salary_mode
# 			self.bank_name = emp.bank_name
# 			self.bank_account_no = emp.bank_ac_no

# 	@frappe.whitelist()
# 	def process_salary_based_on_working_days(self):
# 		self.get_working_days_details(lwp=self.leave_without_pay)
# 		self.calculate_net_pay()

# 	@frappe.whitelist()
# 	def set_totals(self):
# 		self.gross_pay = 0.0
# 		if self.salary_slip_based_on_timesheet == 1:
# 			self.calculate_total_for_salary_slip_based_on_timesheet()
# 		else:
# 			self.total_deduction = 0.0
# 			if hasattr(self, "earnings"):
# 				for earning in self.earnings:
# 					self.gross_pay += flt(earning.amount, earning.precision("amount"))
# 			if hasattr(self, "deductions"):
# 				for deduction in self.deductions:
# 					self.total_deduction += flt(deduction.amount, deduction.precision("amount"))
# 			self.net_pay = flt(self.gross_pay) - flt(self.total_deduction) - flt(self.total_loan_repayment)
# 		self.set_base_totals()

# 	def set_base_totals(self):
# 		self.base_gross_pay = flt(self.gross_pay) * flt(self.exchange_rate)
# 		self.base_total_deduction = flt(self.total_deduction) * flt(self.exchange_rate)
# 		self.rounded_total = rounded(self.net_pay or 0)
# 		self.base_net_pay = flt(self.net_pay) * flt(self.exchange_rate)
# 		self.base_rounded_total = rounded(self.base_net_pay or 0)
# 		self.set_net_total_in_words()

# 	# calculate total working hours, earnings based on hourly wages and totals
# 	def calculate_total_for_salary_slip_based_on_timesheet(self):
# 		if self.timesheets:
# 			self.total_working_hours = 0
# 			for timesheet in self.timesheets:
# 				if timesheet.working_hours:
# 					self.total_working_hours += timesheet.working_hours

# 		wages_amount = self.total_working_hours * self.hour_rate
# 		self.base_hour_rate = flt(self.hour_rate) * flt(self.exchange_rate)
# 		salary_component = frappe.db.get_value(
# 			"Salary Structure", {"name": self.salary_structure}, "salary_component"
# 		)
# 		if self.earnings:
# 			for i, earning in enumerate(self.earnings):
# 				if earning.salary_component == salary_component:
# 					self.earnings[i].amount = wages_amount
# 				self.gross_pay += flt(self.earnings[i].amount, earning.precision("amount"))
# 		self.net_pay = flt(self.gross_pay) - flt(self.total_deduction)

# 	def compute_year_to_date(self):
# 		year_to_date = 0
# 		period_start_date, period_end_date = self.get_year_to_date_period()

# 		salary_slip_sum = frappe.get_list(
# 			"Salary Slip",
# 			fields=["sum(net_pay) as net_sum", "sum(gross_pay) as gross_sum"],
# 			filters={
# 				"employee": self.employee,
# 				"start_date": [">=", period_start_date],
# 				"end_date": ["<", period_end_date],
# 				"name": ["!=", self.name],
# 				"docstatus": 1,
# 			},
# 		)

# 		year_to_date = flt(salary_slip_sum[0].net_sum) if salary_slip_sum else 0.0
# 		gross_year_to_date = flt(salary_slip_sum[0].gross_sum) if salary_slip_sum else 0.0

# 		year_to_date += self.net_pay
# 		gross_year_to_date += self.gross_pay
# 		self.year_to_date = year_to_date
# 		self.gross_year_to_date = gross_year_to_date

# 	def compute_month_to_date(self):
# 		month_to_date = 0
# 		first_day_of_the_month = get_first_day(self.start_date)
# 		salary_slip_sum = frappe.get_list(
# 			"Salary Slip",
# 			fields=["sum(net_pay) as sum"],
# 			filters={
# 				"employee": self.employee,
# 				"start_date": [">=", first_day_of_the_month],
# 				"end_date": ["<", self.start_date],
# 				"name": ["!=", self.name],
# 				"docstatus": 1,
# 			},
# 		)

# 		month_to_date = flt(salary_slip_sum[0].sum) if salary_slip_sum else 0.0

# 		month_to_date += self.net_pay
# 		self.month_to_date = month_to_date

# 	def compute_component_wise_year_to_date(self):
# 		period_start_date, period_end_date = self.get_year_to_date_period()

# 		for key in ("earnings", "deductions"):
# 			for component in self.get(key):
# 				year_to_date = 0
# 				component_sum = frappe.db.sql(
# 					"""
# 					SELECT sum(detail.amount) as sum
# 					FROM `tabSalary Detail` as detail
# 					INNER JOIN `tabSalary Slip` as salary_slip
# 					ON detail.parent = salary_slip.name
# 					WHERE
# 						salary_slip.employee = %(employee)s
# 						AND detail.salary_component = %(component)s
# 						AND salary_slip.start_date >= %(period_start_date)s
# 						AND salary_slip.end_date < %(period_end_date)s
# 						AND salary_slip.name != %(docname)s
# 						AND salary_slip.docstatus = 1""",
# 					{
# 						"employee": self.employee,
# 						"component": component.salary_component,
# 						"period_start_date": period_start_date,
# 						"period_end_date": period_end_date,
# 						"docname": self.name,
# 					},
# 				)

# 				year_to_date = flt(component_sum[0][0]) if component_sum else 0.0
# 				year_to_date += component.amount
# 				component.year_to_date = year_to_date

# 	def get_year_to_date_period(self):
# 		payroll_period = get_payroll_period(self.start_date, self.end_date, self.company)

# 		if payroll_period:
# 			period_start_date = payroll_period.start_date
# 			period_end_date = payroll_period.end_date
# 		else:
# 			# get dates based on fiscal year if no payroll period exists
# 			fiscal_year = get_fiscal_year(date=self.start_date, company=self.company, as_dict=1)
# 			period_start_date = fiscal_year.year_start_date
# 			period_end_date = fiscal_year.year_end_date

# 		return period_start_date, period_end_date

# 	def add_leave_balances(self):
# 		self.set("leave_details", [])

# 		if frappe.db.get_single_value("Payroll Settings", "show_leave_balances_in_salary_slip"):
# 			from hrms.hr.doctype.leave_application.leave_application import get_leave_details

# 			leave_details = get_leave_details(self.employee, self.end_date)

# 			for leave_type, leave_values in leave_details["leave_allocation"].items():
# 				self.append(
# 					"leave_details",
# 					{
# 						"leave_type": leave_type,
# 						"total_allocated_leaves": flt(leave_values.get("total_leaves")),
# 						"expired_leaves": flt(leave_values.get("expired_leaves")),
# 						"used_leaves": flt(leave_values.get("leaves_taken")),
# 						"pending_leaves": flt(leave_values.get("leaves_pending_approval")),
# 						"available_leaves": flt(leave_values.get("remaining_leaves")),
# 					},
# 				)


# def unlink_ref_doc_from_salary_slip(doc, method=None):
# 	"""Unlinks accrual Journal Entry from Salary Slips on cancellation"""
# 	linked_ss = frappe.db.sql_list(
# 		"""select name from `tabSalary Slip`
# 	where journal_entry=%s and docstatus < 2""",
# 		(doc.name),
# 	)
# 	if linked_ss:
# 		for ss in linked_ss:
# 			ss_doc = frappe.get_doc("Salary Slip", ss)
# 			frappe.db.set_value("Salary Slip", ss_doc.name, "journal_entry", "")


# def generate_password_for_pdf(policy_template, employee):
# 	employee = frappe.get_doc("Employee", employee)
# 	return policy_template.format(**employee.as_dict())


# def get_salary_component_data(component):
# 	return frappe.get_value(
# 		"Salary Component",
# 		component,
# 		[
# 			"name as salary_component",
# 			"depends_on_payment_days",
# 			"salary_component_abbr as abbr",
# 			"do_not_include_in_total",
# 			"is_tax_applicable",
# 			"is_flexible_benefit",
# 			"variable_based_on_taxable_salary",
# 		],
# 		as_dict=1,
# 	)


# def get_payroll_payable_account(company, payroll_entry):
# 	if payroll_entry:
# 		payroll_payable_account = frappe.db.get_value(
# 			"Payroll Entry", payroll_entry, "payroll_payable_account"
# 		)
# 	else:
# 		payroll_payable_account = frappe.db.get_value(
# 			"Company", company, "default_payroll_payable_account"
# 		)

# 	return payroll_payable_account


# def calculate_tax_by_tax_slab(
# 	annual_taxable_earning, tax_slab, eval_globals=None, eval_locals=None
# ):
# 	eval_locals.update({"annual_taxable_earning": annual_taxable_earning})
# 	tax_amount = 0
# 	for slab in tax_slab.slabs:
# 		cond = cstr(slab.condition).strip()
# 		if cond and not eval_tax_slab_condition(cond, eval_globals, eval_locals):
# 			continue
# 		if not slab.to_amount and annual_taxable_earning >= slab.from_amount:
# 			tax_amount += (annual_taxable_earning - slab.from_amount + 1) * slab.percent_deduction * 0.01
# 			continue
# 		if annual_taxable_earning >= slab.from_amount and annual_taxable_earning < slab.to_amount:
# 			tax_amount += (annual_taxable_earning - slab.from_amount + 1) * slab.percent_deduction * 0.01
# 		elif annual_taxable_earning >= slab.from_amount and annual_taxable_earning >= slab.to_amount:
# 			tax_amount += (slab.to_amount - slab.from_amount + 1) * slab.percent_deduction * 0.01

# 	# other taxes and charges on income tax
# 	for d in tax_slab.other_taxes_and_charges:
# 		if flt(d.min_taxable_income) and flt(d.min_taxable_income) > annual_taxable_earning:
# 			continue

# 		if flt(d.max_taxable_income) and flt(d.max_taxable_income) < annual_taxable_earning:
# 			continue

# 		tax_amount += tax_amount * flt(d.percent) / 100

# 	return tax_amount


# def eval_tax_slab_condition(condition, eval_globals=None, eval_locals=None):
# 	if not eval_globals:
# 		eval_globals = {
# 			"int": int,
# 			"float": float,
# 			"long": int,
# 			"round": round,
# 			"date": datetime.date,
# 			"getdate": getdate,
# 		}

# 	try:
# 		condition = condition.strip()
# 		if condition:
# 			return frappe.safe_eval(condition, eval_globals, eval_locals)
# 	except NameError as err:
# 		frappe.throw(
# 			_("{0} <br> This error can be due to missing or deleted field.").format(err),
# 			title=_("Name error"),
# 		)
# 	except SyntaxError as err:
# 		frappe.throw(_("Syntax error in condition: {0} in Income Tax Slab").format(err))
# 	except Exception as e:
# 		frappe.throw(_("Error in formula or condition: {0} in Income Tax Slab").format(e))
# 		raise


# def get_lwp_or_ppl_for_date(date, employee, holidays):
# 	LeaveApplication = frappe.qb.DocType("Leave Application")
# 	LeaveType = frappe.qb.DocType("Leave Type")

# 	is_half_day = (
# 		frappe.qb.terms.Case()
# 		.when(
# 			(
# 				(LeaveApplication.half_day_date == date)
# 				| (LeaveApplication.from_date == LeaveApplication.to_date)
# 			),
# 			LeaveApplication.half_day,
# 		)
# 		.else_(0)
# 	).as_("is_half_day")

# 	query = (
# 		frappe.qb.from_(LeaveApplication)
# 		.inner_join(LeaveType)
# 		.on((LeaveType.name == LeaveApplication.leave_type))
# 		.select(
# 			LeaveApplication.name,
# 			LeaveType.is_ppl,
# 			LeaveType.fraction_of_daily_salary_per_leave,
# 			(is_half_day),
# 		)
# 		.where(
# 			(((LeaveType.is_lwp == 1) | (LeaveType.is_ppl == 1)))
# 			& (LeaveApplication.docstatus == 1)
# 			& (LeaveApplication.status == "Approved")
# 			& (LeaveApplication.employee == employee)
# 			& ((LeaveApplication.salary_slip.isnull()) | (LeaveApplication.salary_slip == ""))
# 			& ((LeaveApplication.from_date <= date) & (date <= LeaveApplication.to_date))
# 		)
# 	)

# 	# if it's a holiday only include if leave type has "include holiday" enabled
# 	if date in holidays:
# 		query = query.where((LeaveType.include_holiday == "1"))

# 	return query.run(as_dict=True)


# @frappe.whitelist()
# def make_salary_slip_from_timesheet(source_name, target_doc=None):
# 	target = frappe.new_doc("Salary Slip")
# 	set_missing_values(source_name, target)
# 	target.run_method("get_emp_and_working_day_details")

# 	return target


# def set_missing_values(time_sheet, target):
# 	doc = frappe.get_doc("Timesheet", time_sheet)
# 	target.employee = doc.employee
# 	target.employee_name = doc.employee_name
# 	target.salary_slip_based_on_timesheet = 1
# 	target.start_date = doc.start_date
# 	target.end_date = doc.end_date
# 	target.posting_date = doc.modified
# 	target.total_working_hours = doc.total_hours
# 	target.append("timesheets", {"time_sheet": doc.name, "working_hours": doc.total_hours})

# def get_permission_query_conditions(user):
# 	if not user: user = frappe.session.user
# 	user_roles = frappe.get_roles(user)

# 	if "HR User" in user_roles or "HR Manager" in user_roles:
# 		return
# 	else:
# 		return """(
# 			exists(select 1
# 				from `tabEmployee` as e
# 				where e.name = `tabSalary Slip`.employee
# 				and e.user_id = '{user}')
# 		)""".format(user=user)

# def has_record_permission(doc, user):
# 	if not user: user = frappe.session.user
# 	user_roles = frappe.get_roles(user)
	
# 	if "HR User" in user_roles or "HR Manager" in user_roles:
# 		return True
# 	else:
# 		if frappe.db.exists("Employee", {"name":doc.employee, "user_id": user}):
# 			return True
# 		else:
# 			return False 
