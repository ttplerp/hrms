# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import re
import frappe

from frappe import msgprint
from frappe.utils import cstr, flt, cint, getdate, date_diff, nowdate, today
from frappe.utils.data import get_first_day, get_last_day, add_days
from frappe.model.naming import make_autoname
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from hrms.hr.utils import set_employee_name
from hrms.hr.hr_custom_functions import get_month_details, get_payroll_settings, get_salary_tax
# from hrms.hr.doctype.sws_membership.sws_membership import get_sws_contribution
from erpnext.accounts.accounts_custom_functions import get_number_of_days
from erpnext.custom_utils import nvl
from frappe.desk.reportview import get_match_cond
import operator
import math


class SalaryStructure(Document):
	def autoname(self):
		self.name = make_autoname(self.employee + '/.SST' + '/.#####')

	def validate(self):
		if self.is_active == 'No' and not self.to_date:
			frappe.throw("To Date is mandatory for Non Active Salary Structures")
		self.check_overlap()
		self.validate_amount()
		self.validate_employee()
		self.validate_joining_date()
		self.get_employee_details()
		#set_employee_name(self)
		self.check_multiple_active()
		self.update_salary_structure()

	def on_update(self):
		self.assign_employee_details()

	# Ver 2.0, following method introduced by SHIV on 2018/02/2017
	def validate_salary_component(self):
		dup = {}
		for parentfield in ['earnings', 'deductions']:
			parenttype = 'Earning' if parentfield == 'earnings' else 'Deduction'
			for i in self.get(parentfield):
				# Restricting users from entering earning component under deductions table and vice versa.
				component_type, is_loan_component = frappe.db.get_value("Salary Component", i.salary_component, ["type", "is_loan_component"])
				if parenttype != component_type:
					frappe.throw(_('Salary Component <b>`{1}`</b> of type <b>`{2}`</b> cannot be added under <b>`{3}`</b> table. <br/> <b><u>Reference# : </u></b> <a href="#Form/Salary Structure/{0}">{0}</a>').format(
						self.name, i.salary_component, component_type, parentfield.title()), title="Invalid Salary Component")
				# Checking duplicate entries
				if i.salary_component in ('Basic Pay') and i.salary_component in dup:
					frappe.throw(_("Row#{0} : Duplicate entries not allowed for component <b>{1}</b>.")
								 .format(i.idx, i.salary_component), title="Duplicate Record Found")
				else:
					dup.update({i.salary_component: 1})
				# Validate Loan details
				if parenttype == 'Deduction' and cint(is_loan_component):
					if not i.institution_name:
						frappe.throw(_("Row#{}: <b>Institution Name</b> is mandatory for <b>{}</b>").format(i.idx, i.salary_component))
					elif not i.reference_number:
						frappe.throw(_("Row#{}: <b>Loan Account No.(Reference Number)</b> is mandatory for <b>{}</b>").format(i.idx, i.salary_component))

	@frappe.whitelist()
	def get_employee_details(self):
		emp = frappe.get_doc("Employee", self.employee)
		self.employee_name = emp.employee_name
		self.branch = emp.branch
		self.designation = emp.designation
		self.employment_type = emp.employment_type
		self.employee_group = emp.employee_group
		self.employee_grade = emp.grade
		self.department = emp.department
		self.division = emp.division
		self.section = emp.section
		self.backup_employee = self.employee
		self.business_activity = emp.business_activity

	def get_ss_values(self, employee):
		basic_info = frappe.db.sql("""select bank_name, bank_ac_no
			from `tabEmployee` where name =%s""", employee)
		ret = {'bank_name': basic_info and basic_info[0][0] or '',
			   'bank_ac_no': basic_info and basic_info[0][1] or ''}
		return ret

	def make_table(self, doct_name, tab_fname, tab_name):
		# Ver 1.0 by SSK on 08/08/2016, Following line is commented and the subsequent if condition is added
		#list1 = frappe.db.sql("select name from `tab%s` where docstatus != 2" % doct_name)
		if (tab_fname == 'earnings'):
			list1 = frappe.db.sql(
				"select * from `tab{0}` where `docstatus` != 2 and `type` = 'Earning' and `default` = 1".format(doct_name), as_dict=True)
		else:
			list1 = frappe.db.sql(
				"select * from `tab{0}` where `docstatus` != 2 and `type` = 'Deduction' and `default` = 1".format(doct_name), as_dict=True)

		for li in list1:
			child = self.append(tab_fname, {})
			if(tab_fname == 'earnings'):
				child.salary_component = li.name
				child.amount = flt(li.default_amount)
			elif(tab_fname == 'deductions'):
				child.salary_component = li.name
				child.amount = flt(li.default_amount)

	@frappe.whitelist()
	def make_earn_ded_table(self):
		#self.make_table('Salary Component','earnings','Salary Detail')
		#self.make_table('Salary Component','deductions', 'Salary Detail')
		tbl_list = {'earnings': 'Earning', 'deductions': 'Deduction'}
		for ed in tbl_list:
			sc_list = frappe.db.sql(
				"select * from `tabSalary Component` where `docstatus` != 2 and `type` = '{0}'".format(tbl_list[ed]), as_dict=True)
			for sc in sc_list:
				if sc.default:
					child = self.append(ed, {})
					child.salary_component = sc.name
					if sc.type == 'Earning':
						child.amount = flt(sc.default_amount) if sc.payment_method == 'Lumpsum' else 0
					else:
						child.amount = flt(sc.default_amount)
					vars(self)[sc.field_name] = sc.default
				vars(self)[sc.field_method] = sc.payment_method
				vars(self)[sc.field_value] = flt(sc.default_amount)

	def check_overlap(self):
		existing = frappe.db.sql("""select name from `tabSalary Structure`
			where employee = %(employee)s and
			(
				(%(from_date)s >= ifnull(from_date,'0000-00-00') and %(from_date)s <= ifnull(to_date,'2199-12-31')) or
				(%(to_date)s >= ifnull(from_date,'0000-00-00') and %(to_date)s <= ifnull(to_date,'2199-12-31')) or
				(%(from_date)s <= ifnull(from_date,'0000-00-00') and %(to_date)s >= ifnull(to_date,'2199-12-31')))
			and name!=%(name)s
			and docstatus < 2""",
								 {
									 "employee": self.employee,
									 "from_date": self.from_date,
									 "to_date": self.to_date,
									 "name": self.name or "No Name"
								 }, as_dict=True)

		if existing:
			frappe.throw(_("Salary structure {0} already exist, more than one salary structure for same period is not allowed").format(
				existing[0].name))

	def validate_amount(self):
		if flt(self.net_pay) < 0 and self.salary_slip_based_on_timesheet:
			frappe.throw(_("Net pay cannot be negative"))

	def validate_employee(self):
		old_employee = frappe.db.get_value("Salary Structure", self.name, "employee")
		if old_employee and self.employee != old_employee:
			frappe.throw(_("Employee can not be changed"))

	def validate_joining_date(self):
		joining_date = getdate(frappe.db.get_value("Employee", self.employee, "date_of_joining"))
		if getdate(self.from_date) < joining_date:
			frappe.throw(_("From Date in Salary Structure cannot be lesser than Employee Joining Date."))
		
	def assign_employee_details(self):
		if self.employee:
			doc = frappe.get_doc("Employee", self.employee)
			self.db_set("employee_name", doc.employee_name)
			self.db_set("branch", doc.branch)
			self.db_set("department", doc.department)
			self.db_set("division", doc.division)
			self.db_set("section", doc.section)
			self.db_set("employment_type", doc.employment_type)
			self.db_set("employee_group", doc.employee_group)
			self.db_set("employee_grade", doc.grade)
			self.db_set("designation", doc.designation)
			self.db_set("business_activity", doc.business_activity)

	def check_multiple_active(self):
		if self.is_active == 'Yes':
			result = frappe.db.sql(
				"select 1 from `tabSalary Structure` where employee = %s and is_active = \'Yes\' and name != %s", (self.employee, self.name))
			if result:
				frappe.throw("Can not have multiple 'Active' Salary Structures")

	def clean_deductions(self):
		deductions = []
		for a in self.deductions:
			if a.salary_component not in ("Salary Tax", "Health Contribution", "GIS", "SWS", "PF"):
				deductions.append(a)
		self.deductions = deductions

	def test(self):
		for a in self.deductions:
			frappe.msgprint("{0} ==> {1}".format(a.salary_component, a.amount))

	def get_active_amount(self, rec):
		''' return amount only if the component is active '''
		calc_amt = 0
		if rec.from_date or rec.to_date:
			if rec.to_date and str(rec.to_date) >= str(get_first_day(today())):
				calc_amt = rec.amount
			elif rec.from_date and str(rec.from_date) <= str(get_last_day(today())):
				calc_amt = rec.amount
			else:
				calc_amt = 0
		else:    
			calc_amt = rec.amount

		if rec.parentfield == "deductions":
			if not flt(rec.total_deductible_amount):
				calc_amt = calc_amt
			elif flt(rec.total_deductible_amount) and flt(rec.total_deductible_amount) != flt(rec.total_deducted_amount):
				calc_amt = calc_amt
			else:
				calc_amt = 0
				
		return flt(calc_amt)

	@frappe.whitelist()
	def update_salary_structure(self, new_basic_pay=0, remove_flag=1):
		'''
			This method calculates all the allowances and deductions based on the preferences
			set in the GUI. Calculated values are then checked and updated as follows.
					1) If the calculated component is missing in the existing earnings/deductions
						table then insert a new row.
					2) If the calculated component is found in the existing earnings/deductions
						table but amounts do not match, then update the respective row.
		'''
		self.validate_salary_component()
		basic_pay = comm_allowance = gis_amt = pf_amt = health_cont_amt = tax_amt = basic_pay_arrears = payscale_lower_limit= 0
		total_earning = total_deduction = net_pay = 0
		payscale_lower_limit = frappe.db.get_value("Employee Grade", frappe.db.get_value("Employee",self.employee,"grade"), "lower_limit")
		settings = get_payroll_settings(self.employee)
		settings = settings if settings else {}

		tbl_list = {'earnings': 'Earning', 'deductions': 'Deduction'}
		del_list_all = []
		
		for ed in ['earnings', 'deductions']:
			add_list = []
			del_list = []
			calc_map = []

			sst_map = {ed: []}
			for sc in frappe.db.sql("select * from `tabSalary Component` where `type`='{0}' and ifnull(field_name,'') != ''".format(tbl_list[ed]), as_dict=True):
				sst_map.setdefault(ed, []).append(sc)
			ed_map = [i.name for i in sst_map[ed]]

			for ed_item in self.get(ed):
				# validate component validity dates
				if ed_item.from_date and ed_item.to_date and str(ed_item.to_date) < str(ed_item.from_date):
					frappe.throw(_("<b>Row#{}:</b> Invalid <b>From Date</b> for <b>{}</b> under <b>{}s</b>").format(ed_item.idx, ed_item.salary_component, tbl_list[ed]))

				# ed_item.amount = roundoff(ed_item.amount)
				amount = flt(ed_item.amount,2)

				if ed_item.salary_component not in ed_map:
					if ed == 'earnings':
						if ed_item.salary_component == 'Basic Pay':
							if flt(new_basic_pay) > 0 and flt(new_basic_pay) != flt(amount):
								amount = flt(new_basic_pay)
							basic_pay = amount
							ed_item.amount = basic_pay
						# Following condition added by SHIV on 2019/04/29
						elif frappe.db.exists("Salary Component", {"name": ed_item.salary_component, "is_pf_deductible": 1}):
							basic_pay_arrears += flt(ed_item.amount)
						total_earning += amount
					else:
						''' Ver.3.0.191212 Begins '''
						# Following line commented and subsequent if condition added by SHIV on 2019/12/12
						#total_deduction += round(amount)
						if flt(ed_item.total_deductible_amount) == 0:
							# total_deduction += round(amount)
							total_deduction += amount
						else:
							if flt(ed_item.total_deductible_amount) != flt(ed_item.total_deducted_amount):
								total_deduction += amount
						''' Ver3.0.191212 Ends '''
				else:
					for m in sst_map[ed]:
						if m['name'] == ed_item.salary_component and not self.get(m['field_name']):
							del_list.append(ed_item)
							del_list_all.append(ed_item)

			if remove_flag:
				[self.remove(d) for d in del_list]

			# Calculating Earnings and Deductions based on preferences and values set
			for m in sst_map[ed]:
				calc_amt = 0
				if self.get(m['field_method']) == 'Percent' and flt(self.get(m['field_value'])) < 0:
					frappe.throw(
						_("Percentage cannot be less than 0 for component <b>{0}</b>").format(m['name']), title="Invalid Data")
				elif self.get(m['field_method']) == 'Percent' and flt(self.get(m['field_value'])) > 200:
					frappe.throw(
						_("Percentage cannot exceed 200 for component <b>{0}</b>").format(m['name']), title="Invalid Data")

				if ed == 'earnings':
					if self.get(m['field_name']) and m['field_name'] != 'eligible_for_other_deduction':
						if self.get(m["field_method"]) == 'Percent':
							if m['based_on'] == 'Pay Scale Lower Limit':
								calc_amt = flt(payscale_lower_limit)*flt(self.get(m['field_value']))*0.01
							else:
								calc_amt = flt(basic_pay)*flt(self.get(m['field_value']))*0.01
						else:
							calc_amt = flt(self.get(m['field_value']))
						
						calc_amt = flt(calc_amt,2)
						comm_allowance += flt(calc_amt) if m['name'] == 'Communication Allowance' else 0
						total_earning += calc_amt
						calc_map.append({'salary_component': m['name'], 'amount': calc_amt})
				else:
					if self.get(m['field_name']) and m['name'] == 'SWS':
						sws_amt = flt(settings.get('sws_contribution'))
						calc_amt = sws_amt
						flt(calc_amt,2)
						calc_map.append({'salary_component': m['name'], 'amount': flt(calc_amt)})
					elif self.get(m['field_name']) and m['name'] == 'GIS':
						gis_amt = flt(settings.get("gis"))
						calc_amt = gis_amt
						calc_map.append({'salary_component': m['name'], 'amount': flt(calc_amt)})
					elif self.get(m['field_name']) and m['name'] == 'PF':
						pf_amt = (flt(basic_pay)+flt(basic_pay_arrears))*flt(settings.get("employee_pf"))*0.01
						calc_amt = pf_amt
						calc_map.append({'salary_component': m['name'], 'amount': flt(calc_amt)})
					elif self.get(m['field_name']) and m['name'] == 'Health Contribution':
						health_cont_amt = flt(total_earning)*flt(settings.get("health_contribution"))*0.01
						calc_amt = health_cont_amt
						# frappe.msgprint(str(health_cont_amt))
						calc_map.append({'salary_component': m['name'], 'amount': flt(calc_amt)})
					# elif m['field_name'] == "eligible_for_other_deduction":
					# 	if self.get(m["field_method"]) == 'Percent':
					# 		if m['based_on'] == 'Pay Scale Lower Limit':
					# 			calc_amt = flt(payscale_lower_limit)*flt(self.get(m['field_value']))*0.01
					# 		else:
					# 			calc_amt = flt(basic_pay)*flt(self.get(m['field_value']))*0.01
					# 	else:
					# 		calc_amt = flt(self.get(m['field_value']))
					# 	other_deduction_amt = flt(calc_amt)
					# 	calc_map.append({'salary_component': m['name'], 'amount': flt(calc_amt)})
					else:
						calc_amt = 0

					total_deduction += calc_amt

			# Calculating Salary Tax
			if ed == 'deductions':
				if frappe.db.get_value("Employee Group",frappe.db.get_value("Employee", self.employee, "employee_group"), "calc_sal_tax") != 1:
					calc_amt = get_salary_tax(math.floor(flt(total_earning)-flt(pf_amt)-flt(gis_amt)-(comm_allowance*0.5)))
					calc_amt = flt(calc_amt,2)
				else:
					#Edited by Kinley on 16/12/2022 for Non National Temporary Employees(3% tax on basic)
					sal_tax_per = frappe.db.get_value("Employee Group",frappe.db.get_value("Employee", self.employee, "employee_group"), "tax_percent")
					calc_amt = flt(total_earning)*(flt(flt(sal_tax_per,2)/100,2))
					calc_amt = flt(calc_amt,2)
				total_deduction += calc_amt
				calc_map.append({'salary_component': 'Salary Tax', 'amount': flt(calc_amt)})

			# Updating existing Earnings and Deductions tables
			for c in calc_map:
				found = 0
				for ed_item in self.get(ed):
					# frappe.msgprint(str(ed_item.salary_component)+" "+str(c['salary_component']))
					if str(ed_item.salary_component) == str(c['salary_component']):
						found = 1
						if flt(ed_item.amount) != flt(c['amount']):
							ed_item.amount = flt(c['amount'])
						break

				if not found:
					add_list.append(c)

			[self.append(ed, i) for i in add_list]
			
		self.total_earning   = sum([self.get_active_amount(rec) for rec in self.get("earnings")])
		self.total_deduction = sum([self.get_active_amount(rec) for rec in self.get("deductions")])
		self.net_pay = flt(self.total_earning) - flt(self.total_deduction)
		# self.total_earning = flt(total_earning)
		# self.total_deduction = flt(total_deduction)
		# self.net_pay = flt(total_earning)-flt(total_deduction)

		if flt(self.total_earning)-flt(self.total_deduction) < 0 and not self.get('__unsaved'):
			frappe.throw(_("Total deduction cannot be more than total earning. Salary Structure: {} for Employee {}".format(self.name, self.employee)), title="Invalid Data")
		return del_list_all

def roundoff(amount):
	return math.ceil(amount) if (amount - int(amount)) >= 0.5 else math.floor(amount)
	
@frappe.whitelist()
def make_salary_slip(source_name, target_doc=None, calc_days={}):
	def postprocess(source, target):
		gross_amt = 0.00
		comm_amt = 0.00
		basic_amt = 0.00
		basic_pay_arrears = 0.00
		settings = get_payroll_settings(source.employee)
		m_details = get_month_details(target_doc.fiscal_year, target_doc.month)

		target.gross_pay = 0
		target.total_deduction = 0
		target.net_pay = 0
		target.rounded_total = 0
		target.actual_basic = 0

		if calc_days:
			start_date = calc_days.get("from_date")
			end_date = calc_days.get("to_date")
			days_in_month = calc_days.get("total_days_in_month")
			working_days = calc_days.get("working_days")
			lwp = calc_days.get("leave_without_pay")
			payment_days = calc_days.get("payment_days")
		else:
			return

		# Copy earnings and deductions table from source salary structure
		calc_map = {}
		for key in ('earnings', 'deductions'):
			for d in source.get(key):
				amount = flt(d.amount,2)
				if frappe.db.get_value("Payroll Entry",target.payroll_entry,"validate_attendance") == 1 and frappe.db.get_value("Salary Component", d.salary_component, "disable_attendance_check") == 0:
					per_day = flt(d.amount)/30
					attendance = frappe.db.sql("""
						select count(a.name) from `tabAttendance` a where a.status = 'Absent'
						and a.attendance_date between '{}' and '{}'
						and a.employee = '{}'
					""".format(start_date, end_date, source.employee))[0][0]
					amount = flt(d.amount - (flt(per_day)*flt(attendance)),2)
				deductible_amt = 0.0
				deducted_amt = 0.0
				outstanding_amt = 0.0

				if d.from_date:
					if (start_date <= d.from_date <= end_date) or ((d.from_date <= end_date) and (nvl(d.to_date, end_date) >= start_date)):
						if key == 'deductions':
							if flt(d.total_deductible_amount) > 0:
								if flt(d.total_outstanding_amount) > 0:
									if flt(amount) >= flt(d.total_outstanding_amount):
										amount = flt(d.total_outstanding_amount)
								else:
									amount = 0
					else:
						amount = 0
				elif d.to_date:
					if (start_date <= d.to_date <= end_date) or ((d.to_date >= start_date) and (nvl(d.from_date, start_date) <= end_date)):
						if key == 'deductions':
							if flt(d.total_deductible_amount) > 0:
								if flt(d.total_outstanding_amount) > 0:
									if flt(amount) >= flt(d.total_outstanding_amount):
										amount = flt(d.total_outstanding_amount)
								else:
									amount = 0
					else:
						amount = 0
				else:
					if key == 'deductions':
						if flt(d.total_deductible_amount) > 0:
							if flt(d.total_outstanding_amount) > 0:
								if flt(amount) >= flt(d.total_outstanding_amount):
									amount = flt(d.total_outstanding_amount)

							else:
								amount = 0

				if flt(d.total_deductible_amount) > 0:
					if flt(d.total_outstanding_amount) > 0:
						deductible_amt = flt(d.total_deductible_amount,2)
						deducted_amt = flt(flt(d.total_deducted_amount) + flt(amount),2)
						outstanding_amt = flt(flt(d.total_outstanding_amount) - flt(amount),2)

				#added by cety to calculate salary tax even if the salary tax is 0 in salary structure
				if key == 'deductions':
					if frappe.db.get_value("Salary Component", d.salary_component, "name") == "Salary Tax":
						if (d.amount or d.default_amount) == 0:
							calc_map.setdefault(key, []).append({
								'salary_component': d.salary_component
							})

				# Leave without pay
				calc_amount = flt(amount,2)
				if key == "earnings" and frappe.db.get_value("Salary Component", d.salary_component, "disable_attendance_check") == 0:
					if d.depends_on_lwp:
						calc_amount = flt(flt(amount)*flt(payment_days)/flt(days_in_month),2)
					else:
						calc_amount = flt(flt(amount)*(flt(working_days)/flt(days_in_month)),2)
				calc_amount = flt(calc_amount,2)
				# following condition added by SHIV on 2021/05/28
				if not flt(calc_amount):
					continue
				calc_map.setdefault(key, []).append({
					'salary_component': d.salary_component,
					'depends_on_lwp': d.depends_on_lwp,
					'institution_name': d.institution_name,
					'reference_type': d.reference_type,
					'reference_number': d.reference_number,
					'bank_branch': d.bank_branch,
					'bank_account_type': d.bank_account_type,
					'ref_docname': d.name,
					'from_date': start_date,
					'to_date': end_date,
					'amount': flt(calc_amount,2),
					'default_amount': flt(amount,2),
					'total_deductible_amount': flt(deductible_amt,2),
					'total_deducted_amount': flt(deducted_amt,2),
					'total_outstanding_amount': flt(outstanding_amt,2),
					'total_days_in_month': flt(days_in_month),
					'working_days': flt(working_days),
					'leave_without_pay': flt(lwp),
					'payment_days': flt(payment_days),
					'bank_account_type': d.bank_account_type,
					'bank_branch': d.bank_branch,
				})

		#Getting Approved OTs
		ot_details = frappe.db.sql("""select  * from `tabOvertime Application` where docstatus = 1 and employee = '{0}' 
			and processed = 0 and workflow_state = 'Recorded' and posting_date <= '{1}'""".format(source.employee, end_date), as_dict =1)
		# frappe.throw(str(ot_details))
		total_overtime_amount = 0.0
		for d in ot_details:
			row = target.append("ot_items",{})
			row.reference    = d.name
			row.ot_date      = d.posting_date
			row.hourly_rate  = d.rate
			row.total_hours  = d.total_hours
			row.total_amount = d.total_amount
			total_overtime_amount += flt(d.total_amount,2)
		target.ot_total = flt(total_overtime_amount,2)
		if total_overtime_amount:
			calc_map['earnings'].append({
				'salary_component': 'Overtime Allowance',
				'from_date' : start_date,
				'to_date': end_date,
				'amount': flt(total_overtime_amount,2),
				'default_amount': flt(total_overtime_amount,2),
				'total_days_in_month' : flt(days_in_month),
				'working_days': flt(working_days),
				'leave_without_pay': flt(lwp),
				'payment_days': flt(payment_days)
				})
		#ends ot logic
		for e in calc_map['earnings']:
			if e['salary_component'] == 'Basic Pay':
				basic_amt = (flt(e['amount']))
			# Following condition added by SHIV on 2019/04/29
			elif frappe.db.exists("Salary Component", {"name": e['salary_component'], "is_pf_deductible": 1}):
				basic_pay_arrears += (flt(e['amount']))
			if e['salary_component'] == 'Communication Allowance':
				comm_amt = (flt(e['amount']))
			gross_amt += flt(e['amount'])

		gross_amt += (flt(target.arrear_amount) + flt(target.leave_encashment_amount))

		# Calculating PF, Group Insurance Scheme, Health Contribution
		sws_amt = pf_amt = gis_amt = health_cont_amt = 0.00
		for d in calc_map['deductions']:
			if not flt(gross_amt):
				d['amount'] = 0
			else:
				if d['salary_component'] == 'SWS':
					# sws_amt = flt(get_sws_contribution(source.employee, end_date))
					sws_amt = flt(settings.get("sws_contribution"))
					calc_amt = sws_amt
					d['amount'] = calc_amt
				if d['salary_component'] == 'PF':
					percent = flt(settings.get("employee_pf"))
					pf_amt = (flt(basic_amt)+flt(basic_pay_arrears))*flt(percent)*0.01
					calc_amt = pf_amt
					# added by phuntsho on feb April 6th 2021
					# calculate employer pf
					employer_percent = flt(settings.get("employer_pf"))
					employer_pf_amount = (flt(basic_amt)+flt(basic_pay_arrears))*flt(employer_percent)*0.01
					employer_pf_amount = employer_pf_amount
					target.employer_pf = employer_pf_amount
					# ----- end of code by phuntsho -----
					d['amount'] = calc_amt
				if d['salary_component'] == 'GIS':
					gis_amt = flt(settings.get("gis"))
					calc_amt = gis_amt
					d['amount'] = calc_amt
				if d['salary_component'] == 'Health Contribution':
					health_cont_amt = flt(gross_amt)*flt(settings.get("health_contribution"))*0.01
					calc_amt = health_cont_amt
					d['amount'] = calc_amt

		# Calculating Salary Tax
		tax_included = 0
		for d in calc_map['deductions']:
			if not flt(gross_amt):
				d['amount'] = 0
			else:
				if d['salary_component'] == 'Salary Tax':
					tax_amt = 0
					if tax_included == 0:
						if frappe.db.get_value("Employee Group",frappe.db.get_value("Employee", source.employee, "employee_group"), "calc_sal_tax") != 1:
							tax_amt = get_salary_tax(math.floor(flt(gross_amt)-flt(pf_amt)-flt(gis_amt)-(comm_amt*0.5)))
							d['amount'] = flt(tax_amt)
							calc_amt = flt(calc_amt,2)
						else:
							#Edited by Kinley on 16/12/2022 for Non National Temporary Employees(3% tax on basic)
							sal_tax_per = frappe.db.get_value("Employee Group",frappe.db.get_value("Employee", source.employee, "employee_group"), "tax_percent")
							calc_amt = flt(gross_amt)*(flt(flt(sal_tax_per,2)/100,2))
							d['amount'] = flt(calc_amt,2)
							calc_amt = flt(calc_amt,2)
							tax_included = 1
		# Appending calculated components to salary slip
		[target.append('earnings', m) for m in calc_map['earnings']]
		[target.append('deductions', m) for m in calc_map['deductions']]

		target.run_method("pull_emp_details")
		target.run_method("calculate_net_pay")

	doc = get_mapped_doc("Salary Structure", source_name, {
		"Salary Structure": {
			"doctype": "Salary Slip",
			"field_map": {
				"total_earning": "gross_pay",
				"name": "salary_structure",
			}
		}
	}, target_doc, postprocess, ignore_child_tables=True)

	return doc
# Ver 2.0, Following method added by SHIV on 2018/02/27


@frappe.whitelist()
def salary_component_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(""" 
			select
				name,
				type,
				payment_method
			from `tabSalary Component`
			where type = %(component_type)s
			and (
				{key} like %(txt)s
				or
				type like %(txt)s
				or
				payment_method like %(txt)s
			)
			{mcond}
			order by
				if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
				if(locate(%(_txt)s, type), locate(%(_txt)s, type), 99999),
				if(locate(%(_txt)s, payment_method), locate(%(_txt)s, payment_method), 99999),
				idx desc,
				name, type, payment_method
			limit %(start)s, %(page_len)s
			""".format(**{
		'key': searchfield,
		'mcond': get_match_cond(doctype)
	}),
		{
		"txt": "%%%s%%" % txt,
			"_txt": txt.replace("%", ""),
			"start": start,
			"page_len": page_len,
			"component_type": 'Earning' if filters['parentfield'] == 'earnings' else 'Deduction'
	})

# Following code added by SHIV on 2020/09/21


def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if "HR User" in user_roles or "HR Manager" in user_roles:
		return
	else:
		return """(
			exists(select 1
				from `tabEmployee` as e
				where e.name = `tabSalary Structure`.employee
				and e.user_id = '{user}')
		)""".format(user=user)

# Following code added by SHIV on 2020/09/21


def has_record_permission(doc, user):
	if not user:
		user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if "HR User" in user_roles or "HR Manager" in user_roles:
		return True
	else:
		if frappe.db.exists("Employee", {"name": doc.employee, "user_id": user}):
			return True
		else:
			return False

	return True

# Following code added by SHIV on 2020/10/02


def get_basic_and_gross_pay(employee, effective_date=today()):
	struc = frappe.db.sql(""" select sst.name,
			sum(case when sd.salary_component = "Basic Pay" then coalesce(sd.amount,0) else 0 end) basic_pay,
			sum(case when (sc.type = 'Earning' and (sd.salary_component = "Basic Pay" or coalesce(sc.field_name,'') != '')) then ifnull(sd.amount,0) else 0 end) gross_pay
		from `tabSalary Structure` sst, `tabSalary Detail` sd, `tabSalary Component` sc
		where sst.employee = '{employee}'
		and '{effective_date}' between sst.from_date and coalesce(sst.to_date,now())
		and sd.parent = sst.name
		and sc.name = sd.salary_component
		order by coalesce(sst.to_date,now()), sst.from_date
		limit 1
	""".format(employee=employee, effective_date=effective_date), as_dict=True)

	if not struc:
		frappe.throw(_("Salary Structure not found"))

	return struc[0]
