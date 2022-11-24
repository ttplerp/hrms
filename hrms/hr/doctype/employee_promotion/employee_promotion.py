# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate
from hrms.utils import update_employee
from datetime import datetime
from dateutil.relativedelta import relativedelta

class EmployeePromotion(Document):
	def validate(self):
		if frappe.get_value("Employee", self.employee, "status") == "Left":
			frappe.throw(_("Cannot promote Employee with status Left"))
		# if self.single_employee:
		# 	self.get_single_employee_promotion_details()

	def before_submit(self):
		if getdate(self.promotion_date) > getdate():
			frappe.throw(_("Employee Promotion cannot be submitted before Promotion Date "),
				frappe.DocstatusTransitionError)
		# return

	def on_submit(self):
		employee = frappe.get_doc("Employee", self.employee)
		employee = update_employee(employee, self.promotion_details, date=self.promotion_date)
		employee.save()
		salary_structure = frappe.db.sql("select ss.name from `tabSalary Structure` ss where ss.employee = '{0}' and ss.is_active = 'Yes'".format(self.employee),as_dict = True)
		sst = frappe.get_doc("Salary Structure", salary_structure[0].name)
		sst.update_salary_structure(self.new_basic_pay)
		sst.save(ignore_permissions = True)

	def on_cancel(self):
		self.update_employee_master(cancel=True)
  
	def update_employee_master(self, cancel=False): 
		if cancel:
			for t in frappe.db.get_all("Employee Promotion", {"employee": self.employee, "name": ("!=", self.name),
					"promotion_date": (">", self.promotion_date), "docstatus": ("!=", 2)}):
				frappe.throw(_("You cannot cancel as there is another promotion record {} following this entry").format(frappe.get_desk_link(self.doctype, t.name)), title="Not Permitted")
			employee = frappe.get_doc("Employee", self.employee)
			for a in self.promotion_details:
				if a.property == "Grade":
					employee.grade = a.current
					new_pro_date = add_years(date,int(frappe.db.get_value("Employee Grade",a.new,"next_promotion_years")))
					employee.promotion_due_date = employee.promotion_due_date - relativedelta(years=int(new_pro_date))
				elif a.property == "Designation":
					employee.designation = a.current
			employee.save(ignore_permissions=True)
			frappe.db.sql("""delete from `tabEmployee Internal Work History` 
				where reference_doctype = "{}" and reference_docname = "{}"
				""".format(self.doctype, self.name))
		salary_structure = frappe.db.sql("select ss.name from `tabSalary Structure` ss where ss.employee = '{0}' and ss.is_acive = 1".format(self.employee))
		if not salary_structure:
			frappe.throw("No Active Salary Structure for selected employee.")
		sst = frappe.get_doc("Salary Structure", salary_structure[0].name)
		sst.update_salary_structure(self.current_basic_pay)
		sst.save(ignore_permissions = True)
# ))
		# else:
		# 	internal_work_history = {
		# 		'department': self.new_department,
		# 		'division': self.new_division,
		# 		'section': self.new_section,
		# 		'branch': self.new_branch,
		# 		'cost_center': self.new_cost_center,
		# 		'reports_to': self.new_reports_to,
		# 		'from_date': self.transfer_date,
		# 		'reference_doctype': self.doctype,
		# 		'reference_docname': self.name
		# 	}
		# 	employee.append("internal_work_history", internal_work_history)

	def get_promotion_details(self, employee):
		data = []
		#------Employee Details-------#
		employee_details = frappe.db.sql("""
			select grade, date_of_joining from `tabEmployee` where name = '{0}'
		""".format(employee), as_dict = True)
		#-----------------------------#

		#------Promotion Details------#
		next_promotion_years = frappe.db.get_value("Employee Grade", employee_details[0].grade, "next_promotion_years")
		promotion_grade = frappe.db.get_value("Employee Grade", employee_details[0].grade, "promotion_grade")
		previous_promotion = frappe.db.sql("""
			select promotion_date from `tabEmployee Promotion` where employee = '{0}' order by creation desc limit 1
		""".format(employee), as_dict = True)
		#-----------------------------#

		#-Validation and Data Setting-#
		if not previous_promotion:
			d1 = datetime.strptime(str(employee_details[0].date_of_joining),'%Y-%m-%d')
			d2 = datetime.strptime(nowdate(), '%Y-%m-%d')
			datediff = relativedelta(d2,d1).years
			if datediff < next_promotion_years:
				frappe.throw("Employee {0} is not eligible for promotion. Insufficient years served in current grade. Current Grade: {1}, Date of Joining: {2}, Years Needed: {3}".format(employee, employee_details[0].grade, employee_details[0].date_of_joining, next_promotion_years))
			else:
				data.append({'property':'Grade','current':employee_details[0].grade,'new':promotion_grade,'fieldname':'grade'})
		else:
			d1 = datetime.strptime(str(previous_promotion[0].promotion_date),'%Y-%m-%d')
			d2 = datetime.strptime(nowdate(), '%Y-%m-%d')
			datediff = relativedelta(d2,d1).years
			if datediff < next_promotion_years:
				frappe.throw("Employee {0} is not eligible for promotion. Insufficient years served in current grade. Current Grade: {1} Previous Promotion Date: {2}, Years Needed: {3}".format(employee, employee_details[0].grade, previous_promotion[0].promotion_date, next_promotion_years))
			else:
				data.append({'property':'Grade','current':employee_details[0].grade,'new':promotion_grade,'fieldname':'grade'})
		#-----------------------------#
		return data



# Following code added by SHIV on 2021/05/14
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if "HR User" in user_roles or "HR Manager" in user_roles:
		return
	else:
		return """(
			exists(select 1
				from `tabEmployee` as e
				where e.name = `tabEmployee Promotion`.employee
				and e.user_id = '{user}')
		)""".format(user=user)

# Following code added by SHIV on 2021/05/14
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
