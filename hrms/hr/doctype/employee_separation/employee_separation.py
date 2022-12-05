# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from erpnext.controllers.employee_boarding_controller import EmployeeBoardingController
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from frappe.utils import today
from frappe.model.mapper import get_mapped_doc
import frappe

class EmployeeSeparation(EmployeeBoardingController):
	def validate(self):
		super(EmployeeSeparation, self).validate()
		validate_workflow_states(self)
		if self.workflow_state != "Approved":
			notify_workflow_states(self)

	def on_submit(self):
		# super(EmployeeSeparation, self).on_submit()
		notify_workflow_states(self)

	def on_update_after_submit(self):
		self.create_task_and_notify_user()

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
			"doctype": "Employee Benefit Claim",
			"fieldmap": {
				"name": "employee_separation_id",
				"employee_grade": "grade",
			},
			"postprocess": update_item
		},
	}

	target_doc = get_mapped_doc("Employee Separation", source_name, mapper, target_doc)

	return target_doc
