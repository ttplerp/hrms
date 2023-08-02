# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
	comma_or, get_fullname, nowdate, money_in_words, get_first_day
from frappe.model.naming import make_autoname
from frappe import _
from frappe import msgprint
import datetime
import calendar

class SalaryIncrement(Document):
	def autoname(self):
		self.name = make_autoname(str(self.employee) + '/.INC/.' + str(self.fiscal_year)+str(self.get_month_id())+ '/.#####')
		
	def validate(self):
		self.validate_dates()
		self.validate_increment()

	def on_submit(self):
		self.update_increment(self.new_basic)

	def on_cancel(self):
		self.update_increment(self.old_basic)
		
	def get_month_id(self):
		month_id = list(calendar.month_name).index(self.month)
		return str(month_id).rjust(2,"0")

	def update_increment(self, amount=0):
		if self.salary_structure and amount:
			sst = frappe.get_doc("Salary Structure", self.salary_structure)
			sst.update_salary_structure(amount)
			sst.save(ignore_permissions = True)
   
	def validate_dates(self):
		cur_year = getdate(nowdate()).year
		cur_month= getdate(nowdate()).month

		if int(self.fiscal_year) > int(cur_year):
			frappe.throw(_("Salary Increment not allowed for future years"), title="Invalid Data")

		if int(self.fiscal_year) < int(cur_year):
			frappe.throw(_("Salary Increment not allowed for past years"), title="Invalid Data")
	
	def validate_increment(self):
		# if self.employee and not frappe.db.exists("Employee", {"name": self.employee, "increment_cycle": self.month}):
		# 	frappe.throw(_('Invalid increment cycle `<b>{0}</b>` for employee <a href="#Form/Employee/{1}">{1}: {2}</a>').format(self.month,self.employee,self.employee_name), title="Invalid Data")
			
		inc_list = frappe.db.sql("""
		select name
		from `tabSalary Increment`
		where employee = '%s'
		and fiscal_year = '%s'
		and month = '%s'
		and salary_structure = '%s'
		and docstatus = 1
		""" % (self.employee, self.fiscal_year, self.month, self.salary_structure))

		if inc_list:
			frappe.throw(_("Salary Increment is already processed for Employee '{0}: {1}'\
					for the month {2}").format(self.employee, self.employee_name, \
					self.month+"-"+str(self.fiscal_year), self.fiscal_year))

	# Following method created by SHIV on 2018/10/10
	def update_employee_details(self):
		doc = frappe.get_doc("Employee", self.employee)
		self.employee_name      = doc.employee_name
		self.employment_type    = doc.employment_type
		self.employee_group     = doc.employee_group
		# self.grade  = doc.grade
		self.date_of_reference  = doc.date_of_joining
		self.company            = doc.company
		self.branch             = doc.branch
		self.department         = doc.department
		# self.division           = doc.division
		# self.section            = doc.section
		self.designation		= doc.designation

	# Following method created by SHIV on 2018/10/10
	def reset_amounts(self):
		self.salary_structure = None
		self.old_basic = 0
		self.increment = 0
		self.new_basic = 0
		self.payscale_minimum = 0
		self.payscale_increment_method = None
		self.payscale_increment = 0
		self.payscale_maximum = 0
		self.calculated_factor = 0
		self.calculated_increment = 0

	# Following method created by SHIV on 2018/10/10
	def get_employee_payscale(self, employee):
		effective_date = "-".join([self.fiscal_year, self.get_month_id(), "01"])
		old_basic = 0
		new_basic = 0
		increment = 0
		total_months = 0
		if employee:
			salary_structure = get_salary_structure(employee,effective_date)
			if salary_structure:
				sst_doc = frappe.get_doc("Salary Structure", salary_structure)
				date_of_reference = sst_doc.from_date if getdate(sst_doc.from_date) < getdate(frappe.db.get_value("Employee",employee,"date_of_joining")) else frappe.db.get_value("Employee",employee,"date_of_joining")
				for d in sst_doc.earnings:
					if d.salary_component == 'Basic Pay':
						old_basic = flt(d.amount)

				# Fetching employee group settings
				group_doc = frappe.get_doc("Employee Group", frappe.db.get_value("Employee",employee,"employee_group"))
				minimum_months = group_doc.minimum_months
				total_months = frappe.db.sql("""
							select (
								case
									when day('{0}') > 1 and day('{0}') <= 15
									then timestampdiff(MONTH,'{0}','{1}')+1 
									else timestampdiff(MONTH,'{0}','{1}')       
								end
								) as no_of_months
				""".format(str(date_of_reference),str(effective_date)))[0][0]
				
				# Fetching Payscale from employee grade
				employee_group= frappe.get_doc("Employee Group", frappe.db.get_value("Employee",employee,"employee_group"))
				self.payscale_minimum   = employee_group.lower_limit
				self.payscale_increment = employee_group.increment
				self.payscale_maximum   = employee_group.upper_limit 

				# Calculating increment
				# if flt(total_months) >= flt(minimum_months):
				# 	calculated_factor    = 1 if flt(total_months)/12 >= 1 else round(flt(total_months if cint(group_doc.increment_prorated) else 12)/12,2)				
				# 	calculated_increment = (flt(old_basic)*flt(payscale_increment)*0.01) if payscale_increment_method == 'Percent' else flt(payscale_increment)
				# 	if cint(group_doc.increment_prorated):
				# 		calculated_increment = round((flt(calculated_increment)/12)*(flt(total_months) if flt(total_months) < 12 else 12))
						
				# 	increment = flt(calculated_increment)
				# 	new_basic = flt(old_basic) + flt(increment)
				# else:
				new_basic = flt(flt(old_basic)+flt(increment),2)
			return new_basic, increment, old_basic

def get_salary_structure(employee, effective_date):
	sst = frappe.db.sql("""
			select name from `tabSalary Structure`
			where employee = '{0}'
			and is_active = 'Yes'
			and ifnull(to_date,'{1}') >= '{1}'
			and from_date <= ifnull(to_date,'{1}') 
			order by ifnull(to_date,'{1}'),from_date desc limit 1
		""".format(employee,str(effective_date)))

	if sst:
		return sst[0][0]
	else:
		frappe.throw(_('No Active Salary Structure found for the employee <a style="color: green" href="#Form/Employee/{0}">{0}</a>').format(employee))

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabSalary Increment`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabSalary Increment`.employee
				and `tabEmployee`.user_id = '{user}')
	)""".format(user=user)