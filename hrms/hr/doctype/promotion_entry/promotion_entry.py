# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT, date_diff, get_last_day
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba
import math

class PromotionEntry(Document):
	def onload(self):
		if not self.docstatus==1 or self.promotions_submitted:
				return

		# check if salary increments were manually submitted
		entries = frappe.db.count("Employee Promotion", {'promotion_entry': self.name, 'docstatus': 1}, ['name'])
		if cint(entries) == len(self.employees):
				self.set_onload("submitted_ep", True)

	def validate(self):
		self.set_month_dates()
		self.check_increment_cycle()

	def on_submit(self):
		self.create_employee_promotions()

	def before_submit(self):
		self.check_increment_cycle()

	def on_cancel(self):
		# if self.promotions_submitted == 1:
		# 	frappe.throw("Please cancel employee promotions first.")
		self.remove_employee_promotions()

	@frappe.whitelist()
	def check_increment_cycle(self):
		same_cycle = []
		for a in self.employees:
			increment_cycle = frappe.db.get_value("Employee", a.employee, "increment_cycle")
			promotion_cycle = frappe.db.get_value("Employee", a.employee, "promotion_cycle")
			increment_entry = frappe.db.sql("""
                    select ie.name from `tabIncrement Entry` ie, `tabIncrement Employee Detail` ied where ied.parent = ie.name
                    and ie.fiscal_year = '{0}'
                    and ie.month_name = '{1}'
                    and ied.employee = '{2}'
                                   """.format(self.fiscal_year, self.month_name, a.employee))
			if promotion_cycle == increment_cycle and (increment_entry == None or increment_entry == []):
				same_cycle.append({"Employee ID": a.employee, "Employee Name": a.employee_name})
		if same_cycle != []:
			frappe.throw("Following employees have increment cycle in the month {0}, Please run Increment Entry for these employees first. List: {1}".format(self.month_name,same_cycle))

	def get_emp_list(self, process_type=None):
		self.set_month_dates()

		cond = self.get_filter_condition()
		# cond += self.get_joining_relieving_condition()

		if not self.fiscal_year or not self.month_name:
			frappe.throw("Please select Fiscal Year and Month.")

		if self.month_name == "January":
			pe_date = self.fiscal_year+"-01-01"
		elif self.month_name == "July":
			pe_date = self.fiscal_year+"-07-01"
		# query =	"""
		# 	select t1.name as employee, t1.employee_name, t1.department, t1.designation, t1.grade as employee_grade
		# 	from `tabEmployee` t1
		# 	where t1.status = 'Active' and
		# 	employment_type not in ('Contract','Probation')
		# 	and exists(select 1
		# 			from `tabEmployee Internal Work History` as t3
		# 			where t3.parent = t1.name
		# 			and ifnull(TIMESTAMPDIFF(YEAR, ifnull(t3.from_date, t1.date_of_joining), CURDATE()),0) >= (select next_promotion_years from `tabEmployee Grade` g where g.name = t1.grade and t3.grade = t1.grade)
		# 	)
		# 	and t1.promotion_due_date = '{}'
		# 	and t1.promotion_cycle = '{}'
		# 	{}
		# 	order by t1.branch, t1.name
		# """.format(pe_date, self.month_name, cond)
		query = """select t1.name as employee, t1.employee_name, t1.department, t1.designation, t1.grade as employee_grade 
					from `tabEmployee` t1 
					where t1.status = 'Active' 
					and t1.employment_type not in ('Contract','Probation') 
					and t1.promotion_due_date = "{}" 
					and t1.promotion_cycle = "{}" 
					and exists(select 1
							from `tabSalary Structure` t2
							where t2.employee = t1.name
							and t2.is_active = "Yes")
					{} 
					order by t1.branch, t1.name """.format(pe_date, self.month_name, cond)
		# frappe.msgprint(query)
		emp_list = frappe.db.sql(query, as_dict=True)
		emp = []
		# frappe.throw(query)
		# emp_list = frappe.db.sql("""
		# 	select t1.name as employee, t1.employee_name, t1.department, t1.designation, t1.grade as employee_grade
		# 	from `tabEmployee` t1
		# 	where t1.status = 'Active' and
		# 	employment_type not in ('Contract','Probation')
		# 	and t1.promotion_due_date = '{}'
		# 	and t1.promotion_cycle = '{}'
		# 	{}
		# 	order by t1.branch, t1.name
		# """.format(pe_date, self.month_name, cond), as_dict=True)
		# frappe.throw(emp_list)
		for e in emp_list:
			latest = frappe.db.sql("""
					select name from `tabEmployee Internal Work History` where parent = '{0}' and promotion_due_date is not NULL order by idx desc limit 1
                """.format(e.employee), as_dict = True)
			if latest:
				# is_eligible = frappe.db.sql("""
				# 	select 1
				# 	from `tabEmployee Internal Work History` t3, `tabEmployee` t1
				# 	where t3.parent = t1.name
				# 	and t3.reference_doctype = 'Employee Promotion'
				# 	and ifnull(TIMESTAMPDIFF(YEAR, t3.from_date, CURDATE()),0) >= (select next_promotion_years from `tabEmployee Grade` g where g.name = t1.grade and t3.grade = t1.grade)
				# 	and t1.name = '{0}' and t3.name = '{1}'
                #                 """.format(e.employee, latest[0].name))
				# is_eligible = frappe.db.sql("""
				# 	select 1
				# 	from `tabEmployee Internal Work History` t3, `tabEmployee` t1
				# 	where t3.parent = t1.name
				# 	and t3.reference_doctype = 'Employee Promotion'
				# 	and t3.promotion_due_date = DATE({2})
				# 	and t1.name = '{0}' and t3.name = '{1}'
                #                 """.format(e.employee, latest[0].name, pe_date))
				is_eligible = frappe.db.sql("""
					select 1
					from `tabEmployee Internal Work History` t3, `tabEmployee` t1
					where t3.parent = t1.name
					and t3.promotion_due_date = '{2}'
					and t1.name = '{0}' and t3.name = '{1}'
                                """.format(e.employee, latest[0].name, pe_date))
				# frappe.msgprint(str(is_eligible))
				# frappe.msgprint(str(e.employee)+" "+str(is_eligible)+" grade:"+str(e.employee_grade))
				if is_eligible:
					salary_structure = frappe.db.sql("select sd.amount as amount, ss.employee_grade from `tabSalary Detail` sd, `tabSalary Structure` ss where sd.parent = ss.name and ss.employee = '{0}' and ss.is_active = 'Yes' and sd.salary_component = 'Basic Pay'".format(e.employee), as_dict = True)
					personal_pay = frappe.db.sql("select sd.amount as amount from `tabSalary Detail` sd, `tabSalary Structure` ss where sd.parent = ss.name and ss.employee = '{0}' and ss.is_active = 'Yes' and sd.salary_component = 'Personal Pay'".format(e.employee), as_dict = True)
					if len(personal_pay) > 0:
						personal_pay = flt(personal_pay[0].amount,2)
					else:
						personal_pay = 0
					new_grade, new_basic_pay = self.get_additional_details(e.employee, salary_structure[0].amount, personal_pay)
					emp.append({"employee":e.employee, "employee_name": e.employee_name, "department": e.department, "designation": e.designation, "employee_grade": e.employee_grade, "current_basic_pay": salary_structure[0].amount, "new_basic_pay": new_basic_pay, "new_employee_grade": new_grade})
			else:
				# is_eligible = frappe.db.sql("""
				# 	select 1 from
				# 	`tabEmployee` t1
				# 	where ifnull(TIMESTAMPDIFF(YEAR, t1.date_of_joining, CURDATE()),0) >= (select next_promotion_years from `tabEmployee Grade` g where g.name = t1.grade)
                #     and t1.name = '{}'            
                #             """.format(e.employee))
				is_eligible = frappe.db.sql("""
					select 1 from
					`tabEmployee` t1
					where t1.promotion_due_date = '{}'
                    and t1.name = '{}'            
                            """.format(pe_date, e.employee))
				if is_eligible:
					salary_structure = frappe.db.sql("select sd.amount as amount,  ss.employee_grade from `tabSalary Detail` sd, `tabSalary Structure` ss where sd.parent = ss.name and ss.employee = '{0}' and ss.is_active = 'Yes' and sd.salary_component = 'Basic Pay'".format(e.employee), as_dict = True)
					personal_pay = frappe.db.sql("select sd.amount as amount from `tabSalary Detail` sd, `tabSalary Structure` ss where sd.parent = ss.name and ss.employee = '{0}' and ss.is_active = 'Yes' and sd.salary_component = 'Personal Pay'".format(e.employee), as_dict = True)
					if len(personal_pay) > 0:
						personal_pay = flt(personal_pay[0].amount,2)
					else:
						personal_pay = 0
					new_grade, new_basic_pay = self.get_additional_details(e.employee, salary_structure[0].amount, personal_pay)
					emp.append({"employee":e.employee, "employee_name": e.employee_name, "department": e.department, "designation": e.designation, "employee_grade": e.employee_grade, "current_basic_pay": salary_structure[0].amount, "new_basic_pay": new_basic_pay, "new_employee_grade": new_grade})		
		# it = iter(emp)
		# emp_dict = dict(zip(it, it))
		# frappe.msgprint(str(emp))
		return emp

	def get_additional_details(self, employee, basic_pay, personal_pay):
		emp = frappe.get_doc("Employee", employee)
		current_increment = frappe.db.get_value("Employee Grade", emp.grade, "increment")
		new_grade = frappe.db.get_value("Employee Grade", emp.grade, "promotion_grade")
		if not new_grade:
			frappe.throw("Promote to Grade not set for Employee {}".format(employee))
		new_lower_limit = frappe.db.get_value("Employee Grade", new_grade, "lower_limit")
		new_increment = frappe.db.get_value("Employee Grade", new_grade, "increment")
		new_upper_limit = frappe.db.get_value("Employee Grade", new_grade, "upper_limit")
		# if personal_pay > 0:
		# 	ratio = ((flt(basic_pay) + flt(personal_pay))-flt(new_lower_limit))/flt(new_increment)
		# else:
		ratio = ((flt(basic_pay) + flt(personal_pay) + flt(new_increment))-flt(new_lower_limit))/flt(new_increment)
		if flt(str(ratio).split(".")[1]) >= 0.01 and ratio > 0:				
			ratio = math.ceil(ratio)
		elif flt(str(ratio).split(".")[1]) == 0 and ratio > 0:
			ratio += 1
		else:
			ratio = 0
		new_basic_increment = (ratio*flt(new_increment))+flt(new_lower_limit)
		if new_basic_increment > new_upper_limit:
			new_basic_increment = new_upper_limit

		# if flt(new_basic_increment) > flt(new_lower_limit): 
		# 	while True:
		# 		new_lower_limit += new_increment
		# 		amount = new_lower_limit
		# 		if new_lower_limit >= new_basic_increment:
		# 			break
		# else:
		amount = new_basic_increment
		return new_grade, amount

	@frappe.whitelist()
	def fill_employee_details(self):
		self.set('employees', [])
		employees = self.get_emp_list()
		if not employees:
			frappe.throw(_("No employees for the mentioned criteria"))

		for d in employees:
			self.append('employees', d)

		self.number_of_employees = len(employees)

	def get_filter_condition(self):
		self.check_mandatory()

		cond = ''
		
		for f in ['company', 'branch', 'department', 'designation', 'employee']:
			if self.get(f):
				cond += " and t1." + f + " = '" + self.get(f).replace("'", "\'") + "'"

		return cond

	# def get_joining_relieving_condition(self):
	# 	cond = """
	# 		and ifnull(t1.date_of_joining, '0000-00-00') <= '%(end_date)s'
	# 		and ifnull(t1.relieving_date, '2199-12-31') >= '%(start_date)s'
	# 	""" % {"start_date": self.start_date, "end_date": self.end_date}
	# 	return cond

	# following method created by SHIV on 2020/10/20
	def set_month_dates(self):
		months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
		month = str(int(months.index(self.month_name))+1).rjust(2,"0")

		month_start_date = "-".join([str(self.fiscal_year), month, "01"])
		month_end_date   = get_last_day(month_start_date)

		self.start_date = month_start_date
		self.end_date = month_end_date
		# self.month_name = month

	def check_mandatory(self):
		# following line is replaced by subsequent by SHIV on 2020/10/20
		for fieldname in ['company', 'fiscal_year']:
			if not self.get(fieldname):
				frappe.throw(_("Please set {0}").format(self.meta.get_label(fieldname)))

	@frappe.whitelist()
	def create_employee_promotions(self):
		"""
			Creates promotion for selected employees if already not created
		"""
		self.check_permission('write')
		self.created = 1
		emp_list = [d['employee'] for d in self.get_emp_list()]

		if emp_list:
			args = frappe._dict({
				"company": self.company,
				"posting_date": self.posting_date,
				"fiscal_year": self.fiscal_year,
				"month": self.month_name,
				"promotion_entry": self.name
			})
			if len(emp_list) > 500:
				frappe.enqueue(create_employee_promotion_for_employees, timeout=600, employees=emp_list, args=args)
			else:
				create_employee_promotion_for_employees(emp_list, args=args, publish_progress=False)
				# since this method is called via frm.call this doc needs to be updated manually
				self.reload()

	@frappe.whitelist()
	def get_employee_promotion_list(self, ep_status, as_dict=False):
		"""
			Returns list of employee promotions based on selected criteria
		"""
		cond = self.get_filter_condition()
		# query = """
		# 	select t1.name from `tabEmployee Promotion` t1, `tabEmployee` t2
		# 	where t1.employee = t2.name and t2.promotion_cycle = '{}' t1.docstatus = '{}' {}
		# 	and t1.promotion_entry = '{}'
		# """.format(self.month_name, ep_status, cond, self.name)
		# frappe.throw(query)
		ep_list = frappe.db.sql("""
			select t2.name from `tabEmployee Promotion` t2, `tabEmployee` t1
			where t2.employee = t1.name and t1.promotion_cycle = %s and t2.docstatus = %s %s
			and t2.promotion_entry = %s
		""" % ('%s', '%s', cond, '%s'), (self.month_name, ep_status, self.name), as_dict=as_dict)
		return ep_list

	@frappe.whitelist()
	def remove_employee_promotions(self):
		self.check_permission('write')
		ep_list = self.get_employee_promotion_list(ep_status=0)
		if len(ep_list) > 500:
			frappe.enqueue(remove_employee_promotions_for_employees, timeout=600, promotion_entry=self, employee_promotions=ep_list)
		else:
			remove_employee_promotions_for_employees(self, ep_list, publish_progress=False)

	@frappe.whitelist()
	def submit_employee_promotions(self):
		self.check_permission('write')
		ep_list = self.get_employee_promotion_list(ep_status=0)
		if len(ep_list) > 500:
			frappe.enqueue(submit_employee_promotions_for_employees, timeout=600, promotion_entry=self, employee_promotions=ep_list)
		else:
			submit_employee_promotions_for_employees(self, ep_list, publish_progress=False)

	# def email_salary_slip(self, submitted_ss):
	# 	if frappe.db.get_single_value("HR Settings", "email_salary_slip_to_employee"):
	# 		for ss in submitted_ss:
	# 			ss.email_salary_slip()

def remove_employee_promotions_for_employees(promotion_entry, employee_promotions, publish_progress=True):
	deleted_ep = []
	not_deleted_ep = []
	frappe.flags.via_promotion_entry = True

	count = 0
	for ep in employee_promotions:
		try:
			frappe.delete_doc("Employee Promotion",ep[0])
			deleted_ep.append(ep[0])
		except frappe.ValidationError:
			not_deleted_ep.append(ep[0])

		count += 1
		# if publish_progress:
		# 	frappe.publish_progress(count*100/len(employee_promotions), title = _("Removing Employee Promotions..."))
	# if deleted_ep:
	# 	frappe.msgprint(_("Employee Promotions Removed Successfully"))

	# if not deleted_ep and not not_deleted_ep:
	# 	frappe.msgprint(_("No Employee Promotions found to remove for the above selected criteria OR employee promotion already submitted"))

	# if not_deleted_ep:
	# 	frappe.msgprint(_("Could not submit some Employee Promotions. List: "+str(not_deleted_ep)))

def create_employee_promotion_for_employees(employees, args, publish_progress=True):
	employee_promotion_exists_for = get_existing_employee_promotions(employees, args)
	count=0
	promotion_entry = frappe.get_doc("Promotion Entry", args.promotion_entry)
	# frappe.msgprint(str(args.promotion_entry)+" "+str(frappe.get_doc("Promotion Entry", str(args.promotion_entry))))

	for emp in promotion_entry.get("employees"):
		if emp.employee not in employee_promotion_exists_for:
			args.update({
				"doctype": "Employee Promotion",
				"employee": emp.employee
			})
			ep = frappe.get_doc(args)
			row = ep.append("promotion_details")
			row.property = 'Grade'
			row.current = emp.employee_grade
			row.new = frappe.db.get_value("Employee Grade", emp.employee_grade, "promotion_grade")
			row.fieldname = 'grade'
			if emp.new_designation:
				row_two = ep.append("promotion_details")
				row_two.property = "Designation"
				row_two.current = emp.designation
				row_two.new = emp.new_designation
				row_two.fieldname = "designation"
			# -----------------------Salary Details for Employee Promotion/Salary Fixation----------------#
			old_lower_limit = frappe.db.get_value("Employee Grade", emp.employee_grade, "lower_limit")
			old_increment = frappe.db.get_value("Employee Grade", emp.employee_grade, "increment")
			old_upper_limit = frappe.db.get_value("Employee Grade", emp.employee_grade, "upper_limit")
			new_grade = frappe.db.get_value("Employee Grade", emp.employee_grade, "promotion_grade")
			new_lower_limit = frappe.db.get_value("Employee Grade", new_grade, "lower_limit")
			new_increment = frappe.db.get_value("Employee Grade", new_grade, "increment")
			new_upper_limit = frappe.db.get_value("Employee Grade", new_grade, "upper_limit")
			ep.current_lower_limit = old_lower_limit
			ep.current_increment = old_increment
			ep.current_upper_limit = old_upper_limit
			ep.new_lower_limit = new_lower_limit
			ep.new_increment = new_increment
			ep.new_upper_limit = new_upper_limit
			salary_structure = frappe.db.sql("select sd.amount as amount from `tabSalary Detail` sd, `tabSalary Structure` ss where sd.parent = ss.name and ss.employee = '{0}' and ss.is_active = 'Yes' and sd.salary_component = 'Basic Pay'".format(emp.employee), as_dict = True)
			ep.current_basic_pay = salary_structure[0].amount
			# bp_diff = flt(salary_structure[0].amount) - flt(new_lower_limit)
			# new_increment_div = flt(bp_diff) / flt(new_increment)
			# if new_increment_div < 0:
			# 	new_increment_div = -1 * new_increment_div
			# new_increment_div = math.floor(new_increment_div) + 2
			# new_basic_multiple = new_increment_div * new_increment
			# amount = new_basic_multiple + new_lower_limit
			# if int(salary_structure[0].amount) <= new_lower_limit:
			# 	amount = new_lower_limit + new_increment
			# elif int(salary_structure[0].amount) > new_lower_limit:
			# 	amount = int(salary_structure[0].amount)+new_increment
			ep.new_basic_pay = emp.new_basic_pay
			#----------------------------------End--------------------------------------------------------#

			if args.month == "January":
				ep.promotion_date = args.fiscal_year+"-01-01"
			elif args.month == "July":
				ep.promotion_date = args.fiscal_year+"-07-01"
			ep.insert()
			count+=1

			ied = frappe.get_doc("Promotion Employee Detail", emp.name)
			ied.db_set("employee_promotion", ep.name)
			if publish_progress:
				description = " Processing {}: ".format(ss[0]) + "["+str(count)+"/"+str(len(employees))+"]"
				frappe.publish_progress(count*100/len(set(employees) - set(employee_promotion_exists_for)),
					title = _("Creating Employee Promotions..."), description=description)

	promotion_entry.db_set("promotions_created", 1)
	promotion_entry.notify_update()

def get_existing_employee_promotions(employees, args):
	return frappe.db.sql_list("""
		select distinct employee from `tabEmployee Promotion`
		where docstatus!= 2 and company = %s
			and fiscal_year = %s and month = %s
			and employee in (%s)
	""" % ('%s', '%s', '%s', ', '.join(['%s']*len(employees))),
		[args.company, args.fiscal_year, args.month] + employees)

def submit_employee_promotions_for_employees(promotion_entry, employee_promotions, publish_progress=True):
	submitted_ep = []
	not_submitted_ep = []
	frappe.flags.via_promotion_entry = True

	count = 0
	for ep in employee_promotions:
		ep_obj = frappe.get_doc("Employee Promotion",ep[0])
		if not ep_obj.promotion_details or ep_obj.promotion_details == None or ep_obj.promotion_details == "":
			not_submitted_ep.append(ep[0])
		else:
			try:
				ep_obj.submit()
				submitted_ep.append(ep_obj)
			except frappe.ValidationError:
				not_submitted_ep.append(ep[0])

		count += 1
		if publish_progress:
			frappe.publish_progress(count*100/len(employee_promotions), title = _("Submitting Employee Promotions..."))
	if submitted_ep:
		frappe.msgprint(_("Employee Promotions submitted for promotion cycle {1}, {0}")
			.format(ep_obj.fiscal_year, ep_obj.month))

		promotion_entry.db_set("promotions_submitted", 1)
		promotion_entry.notify_update()

	if not submitted_ep and not not_submitted_ep:
		frappe.msgprint(_("No Employee Promotions found to submit for the above selected criteria OR Employee Promotion already submitted"))

	if not_submitted_ep:
		frappe.msgprint(_("Could not submit some Employee Promotions. List of not submitted promotions: "+str(not_submitted_ep)))
