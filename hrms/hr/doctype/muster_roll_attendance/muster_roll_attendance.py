# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import Criterion
from frappe.utils import (
	cint,
	cstr,
	formatdate,
	get_datetime,
	get_link_to_form,
	getdate,
	nowdate,
)

from frappe.model.document import Document

class MusterRollAttendance(Document):
	def validate(self):
		from erpnext.controllers.status_updater import validate_status

		validate_status(
			self.status, ["Present", "Absent", "Half Day"]
		)
		# validate_active_employee(self.employee)
		self.validate_attendance_date()
		self.validate_duplicate_record()
		self.validate_employee_status()
		
	def validate_attendance_date(self):
		date_of_joining = frappe.db.get_value(
			"Muster Roll Employee", self.mr_employee, "joining_date"
		)
		if date_of_joining and getdate(self.date) < getdate(date_of_joining):
			frappe.throw(
				_("Attendance date can not be less than mr employee's joining date")
		)

	def validate_duplicate_record(self):
		duplicate = get_duplicate_attendance_record(
			self.mr_employee, self.date, self.name
		)

		if duplicate:
			frappe.throw(
				_(
					"Attendance for mr employee {0} is already marked for the date {1}: {2}"
				).format(
					frappe.bold(self.mr_employee),
					frappe.bold(self.date),
					get_link_to_form("Muster Roll Attendance", duplicate[0].name),
				),
				title=_("Duplicate Attendance"),
			)

	def validate_employee_status(self):
		if frappe.db.get_value("Muster Roll Employee", self.mr_employee, "status") == "Inactive":
			frappe.throw(
				_("Cannot mark attendance for an Inactive mr employee {0}").format(
					self.mr_employee
				)
			)

def get_duplicate_attendance_record(mr_employee, date, name=None):
	attendance = frappe.qb.DocType("Muster Roll Attendance")
	query = (
		frappe.qb.from_(attendance)
		.select(attendance.name)
		.where((attendance.mr_employee == mr_employee) & (attendance.docstatus < 2))
	)
	
	query = query.where((attendance.date == date))

	if name:
		query = query.where(attendance.name != name)

	return query.run(as_dict=True)
