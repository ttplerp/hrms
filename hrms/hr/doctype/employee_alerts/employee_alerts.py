# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe

from frappe.model.document import Document

class EmployeeAlerts(Document):
    def validate(self):
        if self.employee:
            employee = frappe.get_doc("Employee", self.employee)
            self.employee_name = employee.name
            self.designation = employee.designation
            self.department = employee.department


# Permission query
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabEmployee Alerts`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabEmployee Alerts`.employee
				and `tabEmployee`.user_id = '{user}')
	)""".format(user=user)



