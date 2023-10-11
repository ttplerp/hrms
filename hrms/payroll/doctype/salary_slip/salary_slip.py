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
		# self.employee_subgroup  = emp.grade
		self.bank_name          = emp.bank_name
		self.bank_account_no    = emp.bank_ac_no
		self.gis_number         = emp.gis_number
		self.gis_policy_number  = emp.gis_policy_number
		self.employment_type    = emp.employment_type
		self.employee_group     = emp.employee_group
		# self.employee_grade     = emp.grade
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
					
					# if not cint(frappe.db.get_value("HR Settings", None, "include_holidays_in_total_working_days")):
					# 		days_in_month -= len(holidays)
					# 		working_days  -= len(calc_holidays)

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

	'''
	def get_leave_details(self, joining_date=None, relieving_date=None, lwp=None):
		# if default fiscal year is not set, get from nowdate
		if not self.fiscal_year:
			self.fiscal_year = get_fiscal_year(nowdate())[0]

		if not self.month:
			self.month = "%02d" % getdate(nowdate()).month
			self.set_month_dates()

		if not joining_date:
			joining_date, relieving_date = frappe.db.get_value("Employee", self.employee,
				["date_of_joining", "relieving_date"])

		working_days = date_diff(self.end_date, self.start_date) + 1
		holidays = self.get_holidays_for_employee(self.start_date, self.end_date)
				
		if not cint(frappe.db.get_value("HR Settings", None, "include_holidays_in_total_working_days")):
			working_days -= len(holidays)
			if working_days < 0:
				frappe.throw(_("There are more holidays than working days this month."))

		if not lwp:
			lwp = self.calculate_lwp(holidays, working_days)
		self.total_days_in_month = working_days 
		self.leave_without_pay = lwp
		payment_days = flt(self.get_payment_days(joining_date, relieving_date)) - flt(lwp)
		self.payment_days = payment_days > 0 and payment_days or 0
	'''
	
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
		#if(frappe.db.get_single_value("HR Settings", "email_salary_slip_to_employee")):
		#	self.email_salary_slip()

		# Ver 1.0 Begins by SSK on 25/08/2016, following block added

		#sst = frappe.get_doc("Salary Structure", self.salary_structure)
		
		'''
		for ssl in self.deductions:
				if (ssl.from_date and ssl.to_date):
						sst = frappe.get_doc("Salary Structure", self.salary_structure)
						for sst in sst.deductions:
								if (ssl.reference_number == sst.reference_number) and \
									(ssl.reference_type == sst.reference_type) and \
									(ssl.salary_component == sst.salary_component):
										sst.total_deducted_amount += ssl.amount
										sst.total_outstanding_amount = (sst.total_deductible_amount-sst.total_deducted_amount) if sst.total_deductible_amount else 0
										sst.save()
		'''
		# Ver 1.0 Ends
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
			# "validation": {
			# 	"docstatus": ["=", 1]
			# }
		},
		# "Sales Taxes and Charges": {
		# 	"doctype": "Sales Taxes and Charges",
		# 	"add_if_empty": True
		# },
		# "Sales Team": {
		# 	"doctype": "Sales Team",
		# 	"add_if_empty": True
		# }
	}

	# if not skip_item_mapping:
	# 	mapper["Sales Order Item"] = {
	# 		"doctype": "Delivery Note Item",
	# 		"field_map": {
	# 			"rate": "rate",
	# 			"name": "so_detail",
	# 			"parent": "against_sales_order",
	# 		},
	# 		"postprocess": update_item,
	# 		"condition": lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
	# 	}

	target_doc = get_mapped_doc("Salary Slip", source_name, mapper, target_doc, set_missing_values)

	return target_doc