# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from frappe.utils import getdate
from datetime import datetime
from dateutil.relativedelta import relativedelta

class EmployeeTransfer(Document):
	def validate(self):
		self.check_duplicate()
		self.validate_transfer_date()

		self.validate_employee_eligibility()
		if frappe.get_value("Employee", self.employee, "status") == "Left":
			frappe.throw(_("Cannot transfer Employee with status Left"))
  
	def before_submit(self):
		if getdate(self.transfer_date) > getdate():
			frappe.throw(_("Employee Transfer cannot be submitted before Transfer Date "),
				frappe.DocstatusTransitionError)

	def on_submit(self):
		self.update_employee_master()
		
	def on_cancel(self):
		self.update_employee_master(cancel=True)
  
	def validate_transfer_date(self):
		for t in frappe.db.get_all("Employee Transfer", {"employee": self.employee, "name": ("!=", self.name),
			"transfer_date": (">", self.transfer_date), "docstatus": ("!=", 2)}):
			frappe.throw(_("Not permitted as there is another transfer record {} following this entry").format(frappe.get_desk_link(self.doctype, t.name)), title="Not Permitted")			

	def check_duplicate(self):
		for t in frappe.db.get_all("Employee Transfer", {"employee": self.employee, "name": ("!=", self.name), "docstatus": ("=", 0)}):
				frappe.throw(_("There is another transfer record {} in process").format(frappe.get_desk_link(self.doctype, t.name)), title="Duplicate Entry")		

	def update_employee_master(self, cancel=False):
		employee = frappe.get_doc("Employee", self.employee)
		employee.department = self.new_department if not cancel else self.old_department
		employee.division	= self.new_division if not cancel else self.old_division
		employee.designation= self.new_designation if not cancel else self.old_designation
		employee.section	= self.new_section if not cancel else self.old_section
		employee.branch		= self.new_branch if not cancel else self.old_branch
		employee.cost_center= self.new_cost_center if not cancel else self.old_cost_center
		employee.expense_approver = self.new_reports_to if not cancel and self.new_reports_to else self.old_reports_to
  
		if cancel:
			for t in frappe.db.get_all("Employee Transfer", {"employee": self.employee, "name": ("!=", self.name),
					"transfer_date": (">", self.transfer_date), "docstatus": ("!=", 2)}):
				frappe.throw(_("You cannot cancel as there is another transfer record {} following this entry").format(frappe.get_desk_link(self.doctype, t.name)), title="Not Permitted")
			frappe.db.sql("""delete from `tabEmployee Internal Work History` 
				where reference_doctype = "{}" and reference_docname = "{}"
				""".format(self.doctype, self.name))
		else:
			internal_work_history = {
				'department': self.new_department,
				'division': self.new_division,
				'section': self.new_section,
				'branch': self.new_branch,
				'cost_center': self.new_cost_center,
				'reports_to': self.new_reports_to,
				'from_date': self.transfer_date,
				'reference_doctype': self.doctype,
				'reference_docname': self.name
			}
			employee.append("internal_work_history", internal_work_history)
		employee.save(ignore_permissions=True)
  
	def validate_employee_eligibility(self):
		if self.transfer_type == "Personal Request":
			date1 = ''
			employment_type = frappe.db.get_value("Employee", self.employee, "employment_type")
			if employment_type == "Probation":
				frappe.throw("Employee on probation cannot apply for transfer.")
			latest_work_history_date = frappe.db.sql("""select 
										from_date 
									from 
										`tabEmployee Internal Work History` 
									where 
										parent = '{0}'
										and reference_doctype = 'Employee Transfer'
									order by idx desc limit 1
            					""".format(self.employee),as_dict=True)

			if latest_work_history_date:
				date1 = latest_work_history_date[0].from_date
			else:
				date_of_joining = frappe.db.sql("""
								select 
									date_of_joining 
								from 
									`tabEmployee` 
								where name = '{0}'
            				""".format(self.employee),as_dict=True)	
				date1 = date_of_joining[0].date_of_joining
				# d1 = datetime.datetime.strptime(str(datetime.datetime.today().strftime('%Y-%m-%d')),'%Y-%m-%d')
			d1 = datetime.strptime(str(date1),'%Y-%m-%d')
			d2 = datetime.strptime(self.transfer_date, '%Y-%m-%d')

			datediff = relativedelta(d2,d1).years
			if datediff < 4:
    				frappe.throw("You are not eligble for transfer since you have not served in your current branch for at least 4 years")
    
	# def validate_user_in_details(self):
	# 	for item in self.transfer_details:
	# 		if item.fieldname == "user_id" and item.new != item.current:
	# 			return True
	# 	return False


# Following code added by SHIV on 2021/05/14
# def get_permission_query_conditions(user):
# 	if not user: user = frappe.session.user
# 	user_roles = frappe.get_roles(user)

# 	if "HR User" in user_roles or "HR Manager" in user_roles:
# 		return
# 	elif "Approver" in user_roles:
# 		approver_id = frappe.db.get_value("Employee", {"user_id":user},"name")
# 		return """(
# 			exists(select 1
# 				from `tabEmployee` as e
# 				where e.name = `tabEmployee Transfer`.employee
# 				and e.reports_to = '{approver_id}')
# 		)""".format(approver_id=approver_id) 
# 	else:
# 		return """(
# 			exists(select 1
# 				from `tabEmployee` as e
# 				where e.name = `tabEmployee Transfer`.employee
# 				and e.user_id = '{user}')
# 		)""".format(user=user)

# Following code added by SHIV on 2020/09/21
# def has_record_permission(doc, user):
# 	if not user: user = frappe.session.user
# 	user_roles = frappe.get_roles(user)
	
# 	if "HR User" in user_roles or "HR Manager" in user_roles:
# 		return True
# 	elif "Approver" in user_roles:
# 		if frappe.db.get_value("Employee", {"name":doc.employee},"reports_to") == frappe.db.get_value("Employee",{"user_id":user},"name"):
# 			return True 
# 	else:
# 		if frappe.db.exists("Employee", {"name":doc.employee, "user_id": user}):
# 			return True
# 		else:
# 			return False 

# 	return True

@frappe.whitelist()
def make_employee_benefit(source_name, target_doc=None, skip_item_mapping=False):
	def update_item(source, target):
		# target.purpose = "Separation"
		target.employee_transfer_id = source.name

	mapper = {
		"Employee Transfer": {
			"doctype": "Employee Benefits",
		},
	}
	target_doc = get_mapped_doc("Employee Transfer", source_name, mapper, target_doc, update_item)
	return target_doc

	
