# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate,flt,cint,today,add_to_date
from frappe.model.document import Document

class OvertimeApplication(Document):
	def validate(self):
		self.validate_dates()
		self.calculate_totals()
		self.validate_eligible_creteria()

	def validate_eligible_creteria(self):
		if "Employee" not in frappe.get_roles(frappe.session.user):
			frappe.msgprint(_("Only employee of {} can apply for Overtime").format(frappe.bold(self.company)), title="Not Allowed", indicator="red", raise_exception=1)

		if cint(frappe.db.get_value('Employee Grade',self.grade,'eligible_for_overtime')) == 0:
			frappe.msgprint(_("You are not eligible for overtime"), title="Not Eligible", indicator="red", raise_exception=1)
	def calculate_totals(self):			
		settings = frappe.get_single("HR Settings")
		overtime_limit_type, overtime_limit = settings.overtime_limit_type, flt(settings.overtime_limit)

		total_hours = 0
		for i in self.get("items"):
			total_hours += flt(i.number_of_hours)
			if flt(i.number_of_hours) > flt(overtime_limit):
				frappe.throw(_("Row#{}: Number of Hours cannot be more than {} hours").format(i.idx, overtime_limit))

			if overtime_limit_type == "Per Day":
				month_start_date = add_to_date(i.to_date, days=-1)
			elif overtime_limit_type == "Per Month":
				month_start_date = add_to_date(i.to_date, months=-1)
			elif overtime_limit_type == "Per Year":
				month_start_date = add_to_date(i.to_date, years=-1)
		
		self.actual_hours = flt(total_hours)
		if flt(total_hours) > flt(overtime_limit):
			frappe.throw(_("Only {} hours accepted for payment").format(overtime_limit))
			self.total_hours = flt(overtime_limit)
			self.total_hours_lapsed = flt(total_hours) - flt(overtime_limit)
		else:
			self.total_hours = flt(self.actual_hours)
		self.total_amount = round(flt(self.total_hours)*flt(self.rate),0)

	# Dont allow duplicate dates
	##
	def validate_dates(self):				
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