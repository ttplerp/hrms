# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe.model.mapper import get_mapped_doc
from erpnext.controllers.employee_boarding_controller import EmployeeBoardingController
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from frappe.utils import today

class EmployeeSeparation(EmployeeBoardingController):
	def validate(self):
		super(EmployeeSeparation, self).validate()
		validate_workflow_states(self)
		notify_workflow_states(self)

	def on_submit(self):
		super(EmployeeSeparation, self).on_submit()
		# notify_workflow_states(self)
	def on_cancel(self):
		super(EmployeeSeparation, self).on_cancel()
		notify_workflow_states(self)
  
@frappe.whitelist()
def make_employee_benefit(source_name, target_doc=None, skip_item_mapping=False):
	def update_item(source, target, source_parent):
		# target.purpose = "Separation"
		target.employee_separation_id = source.name
		target.grade = source.employee_grade
		target.division = frappe.db.get_value("Employee",source.employee,"division")
	mapper = {
		"Employee Separation": {
			"doctype": "Employee Benefits",
			"fieldmap": {
				"name": "employee_separation_id",
				"employee_grade": "grade",
			},
			"postprocess": update_item
		},
	}

	target_doc = get_mapped_doc("Employee Separation", source_name, mapper, target_doc)

	return target_doc

@frappe.whitelist()
def make_separation_clearance(source_name, target_doc=None, skip_item_mapping=False):
	def update_item(source_doc, target_doc, source_parent):
		# target.purpose = "Separation"
		target_doc.employee_separation_id = source_doc.name
		target_doc.cid = frappe.db.get_value("Employee",source_doc.employee,"passport_number")
		target_doc.phone_number = frappe.db.get_value("Employee",source_doc.employee,"cell_number")
		# if frappe.db.get_value("Employee",source_doc.employee,"fixed_line_number"):
		# 	target_doc.fixed_line_number = frappe.db.get_value("Employee",source_doc.employee,"fixed_line_number")
		target_doc.grade = source_doc.employee_grade
		target_doc.division = frappe.db.get_value("Employee",source_doc.employee,"division")
		target_doc.approver = None
		target_doc.approver_name = None
		target_doc.approver_designation = None
	mapper = {
		"Employee Separation": {
			"doctype": "Employee Separation Clearance",
			"field_map":{
				"name": "employee_separation_id",
				"employee_grade": "grade",
			},
			"postprocess": update_item,
		},
		
	}

	target_doc = get_mapped_doc("Employee Separation", source_name, mapper, target_doc)

	return target_doc

# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabEmployee Separation`.owner = '{user}' and `tabEmployee Separation`.docstatus = 0
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabEmployee Separation`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabEmployee Separation`.approver = '{user}' and `tabEmployee Separation`.workflow_state not in ('Draft','Submitted','Rejected','Cancelled') and `tabEmployee Separation`.docstatus = 0)
	)""".format(user=user)
