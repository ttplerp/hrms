# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import add_days, add_years, cint, getdate
from frappe.model.naming import make_autoname
from erpnext.setup.doctype.employee.employee import Employee


class EmployeeMaster(Employee):
	def autoname(self):
		# naming done with combination with joining year, month and 4 digits series
		# if self.old_id:
		# 	self.employee =	self.name = self.old_id
		# 	return
		year_month = str(self.date_of_joining)[2:4] + str(self.date_of_joining)[5:7]
		name = make_autoname('EMP.####')[3:]
		self.employee = self.name = year_month + name

def validate_onboarding_process(doc, method=None):
	"""Validates Employee Creation for linked Employee Onboarding"""
	if not doc.job_applicant:
		return

	employee_onboarding = frappe.get_all(
		"Employee Onboarding",
		filters={
			"job_applicant": doc.job_applicant,
			"docstatus": 1,
			"boarding_status": ("!=", "Completed"),
		},
	)
	if employee_onboarding:
		onboarding = frappe.get_doc("Employee Onboarding", employee_onboarding[0].name)
		onboarding.validate_employee_creation()
		onboarding.db_set("employee", doc.name)


def update_to_date_in_work_history(doc, method=None):
	if not doc.internal_work_history:
		return

	for idx, row in enumerate(doc.internal_work_history):
		if not row.from_date or idx == 0:
			continue

		doc.internal_work_history[idx - 1].to_date = add_days(row.from_date, -1)

	doc.internal_work_history[-1].to_date = None


def update_approver_role(doc, method=None):
	"""Adds relevant approver role for the user linked to Employee"""
	if doc.leave_approver:
		user = frappe.get_doc("User", doc.leave_approver)
		user.flags.ignore_permissions = True
		user.add_roles("Leave Approver")

	if doc.expense_approver:
		user = frappe.get_doc("User", doc.expense_approver)
		user.flags.ignore_permissions = True
		user.add_roles("Expense Approver")


def update_employee_transfer(doc, method=None):
	"""Unsets Employee ID in Employee Transfer if doc is deleted"""
	if frappe.db.exists("Employee Transfer", {"new_employee_id": doc.name, "docstatus": 1}):
		emp_transfer = frappe.get_doc("Employee Transfer", {"new_employee_id": doc.name, "docstatus": 1})
		emp_transfer.db_set("new_employee_id", "")


@frappe.whitelist()
def get_timeline_data(doctype, name):
	"""Return timeline for attendance"""
	from frappe.desk.notifications import get_open_count

	out = {}

	open_count = get_open_count(doctype, name)
	out["count"] = open_count["count"]

	timeline_data = dict(
		frappe.db.sql(
			"""
			select unix_timestamp(attendance_date), count(*)
			from `tabAttendance` where employee=%s
			and attendance_date > date_sub(curdate(), interval 1 year)
			and status in ('Present', 'Half Day')
			group by attendance_date""",
			name,
		)
	)

	out["timeline_data"] = timeline_data
	return out


@frappe.whitelist()
def get_retirement_date(date_of_birth=None):
	if date_of_birth:
		try:
			retirement_age = cint(frappe.db.get_single_value("HR Settings", "retirement_age") or 60)
			dt = add_years(getdate(date_of_birth), retirement_age)
			return dt.strftime("%Y-%m-%d")
		except ValueError:
			# invalid date
			return
