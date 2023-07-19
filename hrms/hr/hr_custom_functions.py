import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, date_diff, nowdate
from frappe.utils.data import get_first_day, get_last_day, add_days
from erpnext.custom_utils import get_year_start_date, get_year_end_date
import json
import logging
from datetime import datetime, timedelta
import datetime
import calendar

def post_leave_credits(today=None):
	"""
		:param today: First day of the month
		:param employee: Employee id for individual allocation
		
		This method allocates leaves in bulk as per the leave credits defined in Employee Group master.
		It is mainly used for allocating monthly and yearly leave credits automatically through hooks.py.
		However, it can also be used for allocating manually if in case the automatic allocation failed
		for some reason.

		To run manually: Just pass the first day of the month to this method as argument. Following example
				allocates monthly credits for the period from '2019-01-01' till '2019-01-31', and yearly
				credits for the period from '2019-01-01' till '2019-12-31' as defined in Employee Group
				master for all the leave types except `Earned Leave`. Monthly credits for `Earned Leave`
				are allocated for the previous month i.e from '2018-12-01' till '2018-12-31'.

				Example:
					# Executing from console
					bench execute erpnext.hr.hr_custom_functions.post_leave_credits --args "'2019-01-01',"
	"""

	# Logging
	logging.basicConfig(format='%(asctime)s|%(name)s|%(levelname)s|%(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
	logger = logging.getLogger(__name__)
	
	today      = getdate(today) if today else getdate(nowdate())
	start_date = ''
	end_date   = ''

	first_day_of_month = 1 if today.day == 1 else 0
	first_day_of_year  = 1 if today.day == 1 and today.month == 1 else 0
		
	# if first_day_of_month or first_day_of_year:
	f_date = get_first_day(add_days(today, -today.day))
	t_date   = get_last_day(f_date)
	elist = frappe.db.sql("""
		select
			t1.name, t1.employee_name, t1.date_of_joining,
			(
			case
				when day(t1.date_of_joining) > 1 and day(t1.date_of_joining) <= 15
				then timestampdiff(MONTH,t1.date_of_joining,'{0}')+1 
				else timestampdiff(MONTH,t1.date_of_joining,'{0}')       
			end
			) as no_of_months,
			t2.leave_type, t2.credits_per_month, t2.credits_per_year,
			t3.is_carry_forward
		from `tabEmployee` as t1, `tabEmployee Group Item` as t2, `tabLeave Type` as t3
		where t1.status = 'Active'
		and t1.date_of_joining <= '{0}'
		and t1.employee_group = t2.parent
		and (t2.credits_per_month > 0 or t2.credits_per_year > 0)
		and t3.name = t2.leave_type
		and not exists(select 1
					  from `tabLeave Allocation` as t4
					  where t4.employee = t1.name
					  and t4.docstatus != 2 
					  and t4.from_date = '{1}'
					  and t4.to_date = '{2}'
					  and t4.leave_type = t3.name
					  )
		order by t1.name, t2.leave_type
	""".format(str(today), f_date, t_date), as_dict=1)

	counter = 0
	for e in elist:
		counter += 1
		leave_allocation = []
		credits_per_month = 0
		credits_per_year = 0
		
		if flt(e.no_of_months) <= 0:
			logger.error("{0}|{1}|{2}|{3}|{4}".format("NOT QUALIFIED",counter,e.name,e.employee_name,e.leave_type))
			continue

		# Monthly credits
		# For Earned Leaved monthly credits are given for previous month
		if flt(e.credits_per_month) > 0 and e.leave_type == "Earned Leave":
			total_working_days = 0
			total_leaves = 0
			start_date = get_first_day(add_days(today, -20))
			end_date   = get_last_day(start_date)
			emplist = frappe.db.sql("""
			select a.employee, a.employee_name, a.from_date, a.to_date 
			from `tabLeave Application` a inner join `tabLeave Type` b on a.leave_type = b.name 
			inner join `tabLeave Type Item` c on b.name = c.parent 
			where (a.from_date between '{0}' and '{1}' or a.to_date 
			between '{0}' and '{1}' or '{2}' between a.from_date and a.to_date)
			and a.employee = '{3}'
			and c.leave_type = 'Earned Leave' 
			and a.docstatus = 1 
			union select employee, employee_name, from_date, to_date 
			from  `tabEmployee Disciplinary Record` 
			where (from_date between '{0}' and '{1}' or to_date between '{0}' and '{1}' 
			or '{2}' between from_date and to_date) and employee = '{3}' 
			and not_guilty_or_acquitted = 0 and docstatus = 1
			""".format(str(start_date), str(end_date), str(today), e.name), as_dict=1)					
			if emplist:
				total_days_in_month = date_diff(end_date, start_date)
				leave_allocation_per_day = flt(e.credits_per_month/total_days_in_month)
				for l in emplist:	
					#Incase of leave within the month
					if l.from_date >= start_date and l.to_date <= end_date:
						total_leaves = total_leaves + date_diff(l.to_date, l.from_date)
					#Incase of leave starting before the month and ending within the month(Not the last day of the month)
					elif l.from_date < start_date and l.to_date < end_date:
						total_leaves = total_leaves + date_diff(l.to_date, start_date)
					#Incase of leave starting within the month(Not first day of the month) and but ends in other months
					elif l.from_date > start_date and l.to_date > end_date:
						total_leaves = total_leaves + date_diff(end_date, l.from_date)
				total_working_days = total_days_in_month - total_leaves

				credits_per_month = flt(total_working_days) * flt(leave_allocation_per_day)
				logger.info("{0}|{1}|{2}|{3}|{4}|{5}".format(e.name,e.employee_name,e.leave_type,flt(total_working_days),flt(credits_per_month),flt(leave_allocation_per_day)))
				
			else:
				# For Earned Leaved monthly credits are given for previous month
				credits_per_month = flt(e.credits_per_month)

		else:
			start_date = get_first_day(today)
			end_date   = get_last_day(start_date)

		leave_allocation.append({
			'from_date': str(start_date),
			'to_date': str(end_date),
			'new_leaves_allocated': flt(credits_per_month)
		})

		# Yearly credits
		if flt(e.credits_per_year) > 0:
			start_date = get_year_start_date(today)
			end_date   = get_year_end_date(start_date)

			leave_allocation.append({
				'from_date': str(start_date),
				'to_date': str(end_date),
				'new_leaves_allocated': flt(e.credits_per_year)
			})

		for la in leave_allocation:
			if not frappe.db.exists("Leave Allocation", {"employee": e.name, "leave_type": e.leave_type, "from_date": la['from_date'], "to_date": la['to_date'], "docstatus": ("<",2)}):
				try:
					doc = frappe.new_doc("Leave Allocation")
					doc.employee             = e.name
					doc.employee_name        = e.employee_name
					doc.leave_type           = e.leave_type
					doc.from_date            = la['from_date']
					doc.to_date              = la['to_date']
					doc.carry_forward        = cint(e.is_carry_forward)
					doc.new_leaves_allocated = flt(la['new_leaves_allocated'])
					doc.submit()
					logger.info("{0}|{1}|{2}|{3}|{4}|{5}".format("SUCCESS",counter,e.name,e.employee_name,e.leave_type,flt(la['new_leaves_allocated'])))
				except Exception as ex:
					logger.exception("{0}|{1}|{2}|{3}|{4}|{5}".format("FAILED",counter,e.name,e.employee_name,e.leave_type,flt(la['new_leaves_allocated'])))
			else:
				logger.warning("{0}|{1}|{2}|{3}|{4}|{5}".format("ALREADY ALLOCATED",counter,e.name,e.employee_name,e.leave_type,flt(la['new_leaves_allocated'])))

	#else:
		#        logger.info("Date {0} is neither beginning of the month nor year".format(str(today)))
		#        return 0
		
def adjust_el():
	# Logging
	logging.basicConfig(format='%(asctime)s|%(name)s|%(levelname)s|%(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
	logger = logging.getLogger(__name__)
	
	####### To overwrite or adjust auto Earned Leave allocation when employee's leave falls within the month ######## 	
	emplist = frappe.db.sql("""
			   select employee, employee_name, from_date, to_date, total_leave_days
			   from `tabLeave Application` where 
			   (from_date between DATE_FORMAT(CURDATE() - INTERVAL 1 MONTH,'%Y-%m-01') and LAST_DAY(CURDATE() - INTERVAL 1 Month)
			   or to_date between DATE_FORMAT(CURDATE() - INTERVAL 1 MONTH,'%Y-%m-01') and LAST_DAY(CURDATE() - INTERVAL 1 Month))
			   and docstatus = 1
			   and exists (select 1
				   from `tabLeave Type` 
				   where dont_allocate_el = 1) 
			   order by employee 	
			   """, as_dict=1)
	
	cur_date = getdate(nowdate())
	first = datetime.date(day=1, month=cur_date.month, year=cur_date.year)

	#Previous Month End Date
	end_date = first - datetime.timedelta(days=1)
	print(end_date)
	#Previous Month Start Date
	start_date = datetime.date(day=1, month=end_date.month, year=end_date.year)
	print(start_date)

	#Get Total no of days in amonth
	total_days = calendar.monthrange(start_date.year, start_date.month)[1]

	for l in emplist:
		print(l.to_date)
		#Incase of leave within the month
		if l.from_date >= start_date and l.to_date <= end_date:
			no_of_leave_days = l.total_leave_days
			allocated_el = flt(0.08 * (total_days - no_of_leave_days))
		#Incase of leave starting before the month and ending within the month(Not the last day of the month)
		elif l.from_date < start_date and l.to_date < end_date:
			first_date = datetime.strptime(l.to_date, "%Y-%m-%d")
			second_date = datetime.strptime(start_date, "%Y-%m-%d")
			no_of_leave_days = (first_date - second_date).days
			allocated_el = flt(0.08 * (total_days - no_of_leave_days))				
		#Incase of leave starting within the month(Not first day of the month) and but ends in other months
		elif l.from_date > start_date and l.to_date > end_date:
			first_date = datetime.strptime(end_date, "%Y-%m-%d")
			second_date = datetime.strptime(l.from_date, "%Y-%m-%d")
			no_of_leave_days = (first_date - second_date).days
			allocated_el = flt(0.08 * (total_days - no_of_leave_days))
		is_carry_forward = frappe.get_value("Leave Type", "Earned Leave", "is_carry_forward")
		print("+++ ")
		#Checks whether EL has been allocated or not	
		if frappe.db.exists("Leave Allocation", {"employee": l.employee, "leave_type": "Earned Leave", "from_date": start_date, "to_date": end_date, "docstatus": ("<",2)}):
			doc = frappe.get_doc("Leave Allocation", {"employee": l.employee, "leave_type":"Earned Leave", "from_date": start_date, "to_date": end_date, "docstatus": ("<",2)})
			total_leaves = flt(doc.total_leaves_allocated) - flt(doc.new_leaves_allocated) + flt(allocated_el)
			doc.db_set("new_leaves_allocated", allocated_el)
			doc.db_set("total_leaves_allocated", total_leaves)
			logger.info("{0}|{1}|{2}|{3}|{4}".format("SUCCESS",l.name,l.employee_name,"Modified Existing allocation",flt(allocated_el)))
		else:
			doc = frappe.new_doc("Leave Allocation")
			doc.employee             = l.employee
			doc.employee_name        = l.employee_name
			doc.leave_type           = "Earned Leave"
			doc.from_date            = start_date
			doc.to_date              = end_date
			doc.carry_forward        = cint(is_carry_forward)
			doc.new_leaves_allocated = flt(allocated_el)
			doc.submit()
			logger.info("{0}|{1}|{2}|{3}|{4}".format("SUCCESS",l.name,l.employee_name,"Created new allocation", flt(allocated_el)))

# +++++++++++++++++++++ VER#2.0#CDCL#886 ENDS +++++++++++++++++++++

##
# Post casual leave on the first day of every month
##
def post_casual_leaves():
	date = getdate(frappe.utils.nowdate())
	if not (date.month == 1 and date.day == 1):
		return 0
	date = add_days(frappe.utils.nowdate(), 10)
	start = get_year_start_date(date);
	end = get_year_end_date(date);
	employees = frappe.db.sql("select name, employee_name from `tabEmployee` where status = 'Active'", as_dict=True)
	for e in employees:
		la = frappe.new_doc("Leave Allocation")
		la.employee = e.name
		la.employee_name = e.employee_name
		la.leave_type = "Casual Leave"
		la.from_date = str(start)
		la.to_date = str(end)
		la.carry_forward = cint(0)
		la.new_leaves_allocated = flt(10)
		la.submit()

##
# Post earned leave on the first day of every month
##
def post_earned_leaves():
	if not getdate(frappe.utils.nowdate()) == getdate(get_first_day(frappe.utils.nowdate())):
		return 0
 
	date = add_days(frappe.utils.nowdate(), -20)
	start = get_first_day(date);
	end = get_last_day(date);
	
	employees = frappe.db.sql("select name, employee_name, date_of_joining from `tabEmployee` where status = 'Active'", as_dict=True)
	for e in employees:
		if cint(date_diff(end, getdate(e.date_of_joining))) > 14:
			la = frappe.new_doc("Leave Allocation")
			la.employee = e.name
			la.employee_name = e.employee_name
			la.leave_type = "Earned Leave"
			la.from_date = str(start)
			la.to_date = str(end)
			la.carry_forward = cint(1)
			la.new_leaves_allocated = flt(2.5)
			la.submit()
		else:
			pass

#function to get the difference between two dates
@frappe.whitelist()
def get_date_diff(start_date, end_date):
	if start_date is None:
		return 0
	elif end_date is None:
		return 0
	else:	
		return frappe.utils.data.date_diff(end_date, start_date) + 1

@frappe.whitelist()
def get_salary_tax(gross_amt):
	tax_amount = max_amount = 0
	max_limit = frappe.db.sql("""select max(b.to_amount)
		from `tabIncome Tax Slab` a, `tabTaxable Salary Slab` b
		where now() between a.effective_from and ifnull(a.effective_till, now())
		and b.parent = a.name
	""")
	if not (gross_amt or max_limit):
		return tax_amount
	max_amount = flt(max_limit[0][0])

	if flt(gross_amt) > flt(max_amount):
		tax_amount = ((flt(gross_amt) - 125000.00) * 0.30) + 20208.00
	else:
		result = frappe.db.sql("""select ifnull(b.tax,0) from
			`tabIncome Tax Slab` a, `tabTaxable Salary Slab` b
			where now() between a.effective_from and ifnull(a.effective_till, now())
			and b.parent = a.name
			and %s between ifnull(b.from_amount,0) and ifnull(b.to_amount,0)
			limit 1
			""", flt(gross_amt))

		if result:
			tax_amount = result[0][0]

	return flt(tax_amount)

# ++++++++++++++++++++ VER#2.0#CDCL#886 BEGINS ++++++++++++++++++++
# VER#2.0#CDCL#886: Following code is commented by SHIV on 06/09/2018
'''		
# Ver 1.0 added by SSK on 03/08/2016, Fetching PF component
@frappe.whitelist()
def get_company_pf(fiscal_year=None, employee=None):
	employee_pf = frappe.db.get_single_value("HR Settings", "employee_pf")
	if not employee_pf:
		frappe.throw("Setup Employee PF in HR Settings")
	employer_pf = frappe.db.get_single_value("HR Settings", "employer_pf")
	if not employer_pf:
		frappe.throw("Setup Employer PF in HR Settings")
	health_contribution = frappe.db.get_single_value("HR Settings", "health_contribution")
	if not health_contribution:
		frappe.throw("Setup Health Contribution in HR Settings")
	retirement_age = frappe.db.get_single_value("HR Settings", "retirement_age")
	if not retirement_age:
		frappe.throw("Setup Retirement Age in HR Settings")
		result = ((flt(employee_pf), flt(employer_pf), flt(health_contribution), flt(retirement_age)),)
	return result

# Ver 1.0 added by SSK on 04/08/2016, Fetching GIS component
@frappe.whitelist()
def get_employee_gis(employee):
		#msgprint(employee);
		result = frappe.db.sql("""select a.gis
				from `tabEmployee Grade` a, `tabEmployee` b
				where b.employee = %s
				and b.employee_group = a.employee_group
				and b.employee_subgroup = a.name
				limit 1
				""",employee);

		if result:
				return result[0][0]
		else:
				return 0.0
'''

# VER#2.0#CDCL#886: Following code is added by SHIV on 06/09/2018
@frappe.whitelist()
def get_payroll_settings(employee=None):
		settings = {}
		if employee:
				settings = frappe.db.sql("""
						select
								e.employee_qualification,
								et.sws_contribution,
								el.gis,
								el.health_contribution,
								el.employee_pf,
								el.employer_pf
						from `tabEmployee` e, `tabEducation Level` el, `tabEmployment Type` et
						where e.name = '{}'
						and et.name = e.employment_type
						and el.name = e.employee_qualification
				""".format(employee), as_dict=True)
		settings = settings[0] if settings else frappe._dict()
		# sws_type = frappe.db.get_single_value('HR Settings', 'sws_type')
		# settings.update({'sws_type': sws_type})
		return settings
# +++++++++++++++++++++ VER#2.0#CDCL#886 ENDS +++++++++++++++++++++

@frappe.whitelist()
def get_month_details(year, month):
	ysd = frappe.db.get_value("Fiscal Year", year, "year_start_date")
	if ysd:
		from dateutil.relativedelta import relativedelta
		import calendar, datetime
		diff_mnt = cint(month)-cint(ysd.month)
		if diff_mnt<0:
			diff_mnt = 12-int(ysd.month)+cint(month)
		msd = ysd + relativedelta(months=diff_mnt) # month start date
		month_days = cint(calendar.monthrange(cint(msd.year) ,cint(month))[1]) # days in month
		med = datetime.date(msd.year, cint(month), month_days) # month end date
		return frappe._dict({
			'year': msd.year,
			'month_start_date': msd,
			'month_end_date': med,
			'month_days': month_days
		})
	else:
		frappe.throw(_("Fiscal Year {0} not found").format(year))

def get_officiating_employee(employee):
	# frappe.msgprint
	if not employee:
		frappe.throw("Employee is Mandatory")
		
	#return frappe.db.sql("select officiate from `tabOfficiating Employee` where docstatus = 1 and revoked != 1 and %(today)s between from_date and to_date and employee = %(employee)s order by creation desc limit 1", {"today": nowdate(), "employee": employee}, as_dict=True)
	qry = "select officiate from `tabOfficiating Employee` where docstatus = 1 and revoked != 1 and %(today)s between from_date and to_date and employee = %(employee)s order by creation desc limit 1"
	officiate = frappe.db.sql(qry, {"today": nowdate(), "employee": employee}, as_dict=True)

	if officiate:
		flag = True
		while flag:
			temp = frappe.db.sql(qry, {"today": nowdate(), "employee": officiate[0].officiate}, as_dict=True)
			if temp:
				officiate = temp
			else:
				flag = False
	return officiate

def update_suspension_record():
	query = "select employee, increment_month, promotion_month from `tabEmployee Disciplinary Record` where docstatus=1 and not_quilty_or_acquitted=0 and DATE_ADD(to_date, INTERVAL 1 DAY) = %(today)s"
	data = frappe.db.sql(query, {"today":nowdate()})
	for d in data:
		emp = frppe.get_doc("Employee", self.employee)
		emp.employment_status = "In Service"
		emp.increment_and_promotion_cycle = d.increment_month
		emp.promotion_cycle = d.promotion_month
		emp.save()

def update_login_details():
    li = frappe.db.sql("""select u.name user, u.mobile_no, 
                       substr(e.name,4) emp_id, e.cell_number, year(e.date_of_joining) year_of_joining
                from `tabUser` u, `tabEmployee` e
                where e.user_id = u.name""", as_dict=True)
    
    counter = 0
    for row in li:
        counter += 1
        print(counter, row.user, row.mobile_no, row.emp_id, row.cell_number, row.year_of_joining)
        
        user = frappe.get_doc("User", row.user)
        user.username = row.emp_id
        # user.new_password = "erp@bobl"+str(row.year_of_joining)
        user.new_password = "bobl@2021"
        if not row.mobile_no and row.cell_number:
            user.mobile_no = row.cell_number
        user.save()
    frappe.db.commit()
		
	
