# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import formatdate, format_datetime
from frappe.utils import add_months, get_first_day, get_last_day, date_diff, cint,flt
import math
import datetime
import calendar


# Wether to proceed with frequency change
PROCEED_WITH_FREQUENCY_CHANGE = False


class HRSettings(Document):
	def validate(self):
		# self.set_naming_series()

		# Based on proceed flag
		global PROCEED_WITH_FREQUENCY_CHANGE
		if not PROCEED_WITH_FREQUENCY_CHANGE:
			self.validate_frequency_change()
		PROCEED_WITH_FREQUENCY_CHANGE = False

	def set_naming_series(self):
		from erpnext.utilities.naming import set_by_naming_series

		set_by_naming_series(
			"Employee",
			"employee_number",
			self.get("emp_created_by") == "Naming Series",
			hide_name_field=True,
		)

	def validate_frequency_change(self):
		weekly_job, monthly_job = None, None

		try:
			weekly_job = frappe.get_doc(
				"Scheduled Job Type", "employee_reminders.send_reminders_in_advance_weekly"
			)

			monthly_job = frappe.get_doc(
				"Scheduled Job Type", "employee_reminders.send_reminders_in_advance_monthly"
			)
		except frappe.DoesNotExistError:
			return

		next_weekly_trigger = weekly_job.get_next_execution()
		next_monthly_trigger = monthly_job.get_next_execution()

		if self.freq_changed_from_monthly_to_weekly():
			if next_monthly_trigger < next_weekly_trigger:
				self.show_freq_change_warning(next_monthly_trigger, next_weekly_trigger)

		elif self.freq_changed_from_weekly_to_monthly():
			if next_monthly_trigger > next_weekly_trigger:
				self.show_freq_change_warning(next_weekly_trigger, next_monthly_trigger)

	def freq_changed_from_weekly_to_monthly(self):
		return self.has_value_changed("frequency") and self.frequency == "Monthly"

	def freq_changed_from_monthly_to_weekly(self):
		return self.has_value_changed("frequency") and self.frequency == "Weekly"

	def show_freq_change_warning(self, from_date, to_date):
		from_date = frappe.bold(format_date(from_date))
		to_date = frappe.bold(format_date(to_date))
		frappe.msgprint(
			msg=frappe._(
				"Employees will miss holiday reminders from {} until {}. <br> Do you want to proceed with this change?"
			).format(from_date, to_date),
			title="Confirm change in Frequency",
			primary_action={
				"label": frappe._("Yes, Proceed"),
				"client_action": "erpnext.proceed_save_with_reminders_frequency_change",
			},
			raise_exception=frappe.ValidationError,
		)


@frappe.whitelist()
def set_proceed_with_frequency_change():
	"""Enables proceed with frequency change"""
	global PROCEED_WITH_FREQUENCY_CHANGE
	PROCEED_WITH_FREQUENCY_CHANGE = True

@frappe.whitelist()
def add_semso_deduction(semso):
	frappe.throw("PLease process from Payroll Entry")
	now_date = datetime.datetime.now()
	start_date = now_date.replace(day=1)
	last_day = calendar.monthrange(now_date.year, now_date.month)[1]
	end_date = now_date.replace(day=last_day)
	percent = int(semso)/100
	# frappe.throw(str(percent))
	li = frappe.db.sql("""
					   SELECT ss.name
					   FROM `tabSalary Structure` ss, `tabEmployee` e
					   WHERE ss.is_active = "Yes"
					   AND ss.employee = e.name
					""", as_dict=True)
	for rec in li:
		basic_pay = 0
		sst = frappe.get_doc("Salary Structure", rec.name)
		for i in sst.earnings:
			if i.salary_component == "Basic Pay":
				basic_pay = flt(i.amount)

		# semso
		if not basic_pay:
			frappe.throw("ERROR: Basic Pay not found")
			
		row = sst.append("deductions", {})
		row.salary_component = "Semso"
		row.salary_component_type = "Deduction"
		row.amount = math.ceil(flt(basic_pay)*flt(percent))
		row.from_date = start_date.date()
		row.to_date = end_date.date()
		row.save(ignore_permissions=True)
		sst.save(ignore_permissions=True)
	frappe.msgprint("Semso Added")
	frappe.db.commit()
	

@frappe.whitelist()
def remove_semso_deduction(semso):
	frappe.throw("PLease process from Payroll Entry")
	li = frappe.db.sql("""
					   SELECT name
					   FROM `tabSalary Detail`
					   WHERE salary_component_type = "Deduction"
					   AND salary_component = "Semso"
					""", as_dict=True)
	if not li:
		frappe.throw("Semso had been alrady removed")
	for rec in li:
		frappe.db.sql("""
			delete from `tabSalary Detail`
			where name ='{}'
		""".format(rec.name))
	frappe.msgprint("Removed Semso from Salary")
	

