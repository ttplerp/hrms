# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, today, getdate, nowdate, add_to_date
from frappe.model.document import Document
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states

class OvertimeApplication(Document):
	def validate(self):
		validate_workflow_states(self)
		self.validate_dates()
		self.calculate_totals()
		self.validate_eligible_criteria()
		if self.workflow_state != "Approved":
			notify_workflow_states(self)
		self.processed = 0

	def validate_eligible_criteria(self):
		if "Employee" not in frappe.get_roles(frappe.session.user):
			frappe.msgprint(_("Only employee of {} can apply for Overtime").format(frappe.bold(self.company)), title="Not Allowed", indicator="red", raise_exception=1)

		# if cint(frappe.db.get_value('Employee Grade',self.grade,'eligible_for_overtime')) == 0:
		# 	frappe.msgprint(_("You are not eligible for overtime"), title="Not Eligible", indicator="red", raise_exception=1)

	def calculate_totals(self):
		total_amount = 0
		total_hours = 0
		for i in self.get("items"):
			total_hours += flt(i.number_of_hours) + flt(i.odd_hours)
			total_amount += i.amount

		self.actual_hours = flt(total_hours)
		self.total_hours = flt(self.actual_hours)
		self.total_amount = round(total_amount,0)

	def on_cancel(self):
		notify_workflow_states(self)

	def on_submit(self):
		notify_workflow_states(self)

	# @frappe.whitelist()
	# def check_for_overtime_eligibility(self):
	# 	if not frappe.db.get_value("Employee Grade", frappe.db.get_value("Employee", self.employee, "grade"), "eligible_for_overtime"):
	# 		frappe.throw(_("Employee is not eligible for Overtime"))

	# Dont allow duplicate dates
	##
	def validate_dates(self):	
		self.posting_date = nowdate() if not self.posting_date else self.posting_date
					
		for a in self.items:
			if not a.from_date or not a.to_date:
				frappe.throw(_("Row#{} : Date cannot be blank").format(a.idx), title="Invalid Date")
			elif getdate(a.to_date) > getdate(today()) or getdate(a.to_date) > getdate(today()):
				frappe.throw(_("Row#{} : Future dates are not accepted").format(a.idx))

			for b in self.items:
				if (a.from_date == b.from_date and a.idx != b.idx) or (a.to_date == b.to_date and a.idx != b.idx):
					frappe.throw(_("Duplicate Dates in rows {}, {}").format(str(a.idx),str(b.idx)))
				elif (a.from_date >= b.from_date and a.from_date <= b.to_date) and a.idx != b.idx:
					frappe.throw(_("Row#{}: From Date/Time is overlapping with Row#{}").format(a.idx, b.idx))
				elif (a.to_date >= b.from_date and a.to_date <= b.to_date) and a.idx != b.idx:
					frappe.throw(_("Row#{}: To Date/Time is overlapping with Row#{}").format(a.idx, b.idx))

			# check if the dates are already claimed
			for i in frappe.db.sql(""" select oa.name from `tabOvertime Application` oa, `tabOvertime Application Item` oai 
						where oa.employee = %(employee)s and oai.parent = oa.name and oa.name != %(name)s and oa.docstatus < 2
						and %(from_date)s <= oai.to_date and %(to_date)s >= oai.from_date
					""", {"employee": self.employee, "name": self.name, "from_date": a.from_date, "to_date": a.to_date}, as_dict=True):
				frappe.throw(_("Row#{}: Dates are overlapping with another request {}").format(a.idx, frappe.get_desk_link("Overtime Application", i.name)))

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabOvertime Application`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabOvertime Application`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabOvertime Application`.approver = '{user}' and `tabOvertime Application`.workflow_state not in ('Draft','Approved','Rejected','Cancelled'))
	)""".format(user=user)