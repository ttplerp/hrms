# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate, money_in_words, getdate
from erpnext.accounts.utils import get_account_currency, get_fiscal_year
from frappe.utils.data import add_days, date_diff
from frappe.model.mapper import get_mapped_doc
from datetime import timedelta
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from erpnext.accounts.doctype.accounts_settings.accounts_settings import get_bank_account

class TravelAuthorization(Document):
	def validate(self):
		self.branch = frappe.db.get_value("Employee", self.employee, "branch")
		self.cost_center = frappe.db.get_value("Employee", self.employee, "cost_center")
		
		validate_workflow_states(self)
		self.validate_project()
		self.assign_end_date()
		self.validate_advance()
		self.set_travel_period()
		self.check_maintenance_project()
		if self.workflow_state != "Approved":
			notify_workflow_states(self)
		if self.training_event:
			self.update_training_event()

	def on_update(self):
		self.set_dsa_rate()
		self.validate_travel_dates()
		self.check_double_dates()
		self.check_leave_applications()

	def before_submit(self):
		self.create_copy()

	def on_submit(self):
		self.check_status()
		self.create_attendance()
		notify_workflow_states(self)

	def before_cancel(self):
		if self.advance_journal:
			for t in frappe.get_all("Journal Entry", ["name"], {"name": self.advance_journal, "docstatus": ("<",2)}):
				msg = '<b>Reference# : <a href="#Form/Journal Entry/{0}">{0}</a></b>'.format(t.name)
				frappe.throw(_("Advance payment for this transaction needs to be cancelled first.<br>{0}").format(msg),title='<div style="color: red;">Not permitted</div>')
		ta = frappe.db.sql("""
			select name from `tabTravel Claim` where ta = '{}' and docstatus != 2
		""".format(self.name))
		if ta:
			frappe.throw("""There is Travel Claim <a href="#Form/Travel%20Claim/{0}"><b>{0}</b></a> linked to this Travel Authorization""".format(ta[0][0]))

	def on_cancel_after_draft(self):
		validate_workflow_states(self)
		notify_workflow_states(self)

	def on_cancel(self):
		if self.travel_claim:
			frappe.throw("Cancel the Travel Claim before cancelling Authorization")
		#if not self.cancellation_reason:
		#	frappe.throw("Cancellation Reason is Mandatory when Cancelling Travel Authorization")
		self.cancel_attendance()	
		if self.training_event:
			self.update_training_event(cancel=True)
		notify_workflow_states(self)

	def on_update_after_submit(self):
		if self.travel_claim:
			frappe.throw("Cannot change once claim is created")
		self.validate_travel_dates(update=True)
		self.check_double_dates()
		self.check_leave_applications()
		#self.assign_end_date()
		self.db_set("end_date_auth", self.items[len(self.items) - 1].date)
		self.cancel_attendance()
		self.create_attendance()

	def update_training_event(self, cancel = False):
		if not cancel:
			if frappe.db.get_value("Training Event Employee", self.training_event_child_ref, "travel_authorization_id") in (None, ''):
				frappe.db.sql("""
					update `tabTraining Event Employee` set travel_authorization_id = '{}' where name = '{}'
					""".format(self.name, self.training_event_child_ref))
		else:
			if frappe.db.get_value("Training Event Employee", self.training_event_child_ref, "travel_authorization_id") == self.name:
				frappe.db.sql("""
					update `tabTraining Event Employee` set travel_authorization_id = NULL where name = '{}'
					""".format(self.training_event_child_ref))

	def create_copy(self):
		self.details = []
		for a in self.items:
			self.append("details", {"date": a.date, "halt": a.halt, "till_date": a.till_date, "no_days": a.no_days, "from_place": a.from_place, "halt_at": a.halt_at})

	def validate_project(self):
		for a in self.items:
			if a.reference_type == "Project":
				if frappe.db.get_value("Project", a.reference_name, "status") in ("Completed", "Cancelled"):
					frappe.throw("Cannot create or submit Journal Entry {} since the project {} is {}".format(self.name, a.reference_name, frappe.db.get_value("Project", a.reference_name, "status")))
			elif a.reference_type == "Task":
				if frappe.db.get_value("Project", frappe.db.get_value("Task", a.reference_name, "project"), "status") in ("Completed", "Cancelled"):
					frappe.throw("Cannot create or submit Journal Entry {} since the project {} is {}".format(self.name, a.reference_name, frappe.db.get_value("Project", frappe.db.get_value("Task", a.reference_name, "project"), "status")))

	def validate_advance(self):
		self.advance_amount     = 0 if not self.need_advance else self.advance_amount
		if self.advance_amount > self.estimated_amount * 0.75:
			frappe.throw("Advance Amount cannot be greater than 75% of Total Estimated Amount")
		self.advance_amount_nu  = 0 if not self.need_advance else self.advance_amount_nu
		self.advance_journal    = None if self.docstatus == 0 else self.advance_journal

	@frappe.whitelist()
	def post_advance_jv(self):
		self.check_advance()

	def set_travel_period(self):
		period = frappe.db.sql("""select min(`date`) as min_date, max(till_date) as max_date
				from `tabTravel Authorization Item` where parent = '{}' """.format(self.name), as_dict=True)
		if period:
			self.from_date 	= period[0].min_date
			self.to_date 	= period[0].max_date

	def check_maintenance_project(self):
		row = 1
		if self.for_maintenance_project == 1:
			for item in self.items:
				if not item.reference_type or not item.reference_name:
					frappe.throw("Project/Maintenance and Reference Name fields are Mandatory in Row {}".format(row),title="Cannot Save")
				row += 1 

	def create_attendance(self):
		for row in self.items:
			from_date = getdate(row.date)
			to_date = getdate(row.till_date) if cint(row.halt) else getdate(row.date)
			noof_days = date_diff(to_date, from_date) + 1
			for a in range(noof_days):
				attendance_date = from_date + timedelta(days=a)
				al = frappe.db.sql("""select name from tabAttendance 
						where docstatus = 1 and employee = %s 
						and attendance_date = %s""", (self.employee, str(attendance_date)), as_dict=True)
				if al:
					doc = frappe.get_doc("Attendance", al[0].name)
					doc.cancel()
					
				#create attendance
				attendance = frappe.new_doc("Attendance")
				attendance.flags.ignore_permissions = 1
				attendance.employee = self.employee
				attendance.employee_name = self.employee_name 
				attendance.attendance_date = attendance_date
				attendance.status = "Tour"
				attendance.branch = self.branch
				attendance.company = frappe.db.get_value("Employee", self.employee, "company")
				attendance.reference_name = self.name
				attendance.submit()

	def cancel_attendance(self):
		if frappe.db.exists("Attendance", {"reference_name":self}):
			frappe.db.sql("delete from tabAttendance where reference_name = %s", (self.name))
	
	def assign_end_date(self):
		if self.items:
			self.end_date_auth = self.items[len(self.items) - 1].date 

	##
	# check advance and make necessary journal entry
	##
	def check_advance(self):
		if self.need_advance:
			if self.currency and flt(self.advance_amount_nu) > 0:
				cost_center = frappe.db.get_value("Employee", self.employee, "cost_center")
				advance_account = frappe.db.get_value("Company", self.company, "travel_advance_account")
				expense_bank_account = get_bank_account(self.branch)
				# expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
				if not cost_center:
					frappe.throw("Setup Cost Center for employee in Employee Information")
				if not expense_bank_account:
					frappe.throw("Setup Default Expense Bank Account for your Branch")
				if not advance_account:
					frappe.throw("Setup Advance to Employee (Travel) in HR Accounts Settings")

				if frappe.db.exists('Company', {'abbr': 'BOBL'}):
					voucher_type = 'Journal Entry'
					naming_series = 'Journal Voucher'
				else:
					voucher_type = 'Bank Entry'
					naming_series = 'Bank Payment Voucher'

				je = frappe.new_doc("Journal Entry")
				je.flags.ignore_permissions = 1 
				je.title = "TA Advance (" + self.employee_name + "  " + self.name + ")"
				je.voucher_type = voucher_type
				je.naming_series = naming_series
				je.remark = 'Advance Payment against Travel Authorization: ' + self.name;
				je.posting_date = self.posting_date
				je.branch = self.branch
				# if self.reference_type:
				# 	je.reference_type = self.reference_type
				# 	je.reference_name = self.reference_name
	
				je.append("accounts", {
					"account": advance_account,
					"party_type": "Employee",
					"party": self.employee,
					"reference_type": "Travel Authorization",
					"reference_name": self.name,
					"cost_center": cost_center,
					"debit_in_account_currency": flt(self.advance_amount_nu),
					"debit": flt(self.advance_amount_nu),
					"business_activity": self.business_activity,
					"is_advance": "Yes"
				})

				je.append("accounts", {
					"account": expense_bank_account,
					"cost_center": cost_center,
					"business_activity": self.business_activity,
					"credit_in_account_currency": flt(self.advance_amount_nu),
					"credit": flt(self.advance_amount_nu),
				})
				
				je.insert(ignore_permissions=True)
				
				#Set a reference to the advance journal entry
				self.db_set("advance_journal", je.name)
	
	##
	# Allow only approved authorizations to be submitted
	##
	def check_status(self):
		if self.document_status == "Rejected":
			frappe.throw("Rejected Documents cannot be submitted")
		return
		if not self.document_status == "Approved":
			frappe.throw("Only Approved Documents can be submitted")

	##
	# Ensure the dates are consistent
	##
	def validate_travel_dates(self, update=False):
		for idx, item in enumerate(self.get("items")):
			if item.halt:
				if not item.till_date:
					frappe.throw(_("Row#{0} : Till Date is Mandatory for Halt Days.").format(item.idx),title="Invalid Date")
			else:
				if not item.till_date:
					item.till_date = item.date

			from_date = item.date
			to_date   = item.date if not item.till_date else item.till_date
			item.no_days   = date_diff(to_date, from_date) + 1
			if update:
				frappe.db.set_value("Travel Authorization Item", item.name, "no_days", item.no_days)
		
		if self.items:
			# check if the travel dates are already used in other travel authorization
			tas = frappe.db.sql("""select t3.idx, t1.name, t2.date, t2.till_date
					from 
						`tabTravel Authorization` t1, 
						`tabTravel Authorization Item` t2,
						`tabTravel Authorization Item` t3
					where t1.employee = "{employee}"
					and t1.docstatus = 1
					and t1.name != "{travel_authorization}"
					and t2.parent = t1.name
					and t3.parent = "{travel_authorization}"
					and (
						(t2.date <= t3.till_date and t2.till_date >= t3.date)
						or
						(t3.date <= t2.till_date and t3.till_date >= t2.date)
					)
			""".format(travel_authorization = self.name, employee = self.employee), as_dict=True)
			for t in tas:
				frappe.throw("Row#{}: The dates in your current Travel Authorization have already been claimed in {} between {} and {}"\
					.format(t.idx, frappe.get_desk_link("Travel Authorization", t.name), t.date, t.till_date))


	##
	# Check if the dates are used under Leave Application
	##
	def check_leave_applications(self):
		las = frappe.db.sql("""select t1.name from `tabLeave Application` t1 
				where t1.employee = "{employee}"
				and t1.docstatus != 2 and  case when t1.half_day = 1 then t1.from_date = t1.to_date end
				and exists(select 1
						from `tabTravel Authorization Item` t2
						where t2.parent = "{travel_authorization}"
						and (
							(t1.from_date <= t2.till_date and t1.to_date >= t2.date)
							or
							(t2.date <= t1.to_date and t2.till_date >= t1.from_date)
						)
				)
		""".format(travel_authorization = self.name, employee = self.employee), as_dict=True)
		for t in las:
			frappe.throw("The dates in your current travel authorization have been used in leave application {}".format(frappe.get_desk_link("Leave Application", t.name)))

	##
	# Send notification to the supervisor / employee
	##
	def sendmail(self, to_email, subject, message):
		email = frappe.db.get_value("Employee", to_email, "user_id")
		if email:
			try:
				frappe.sendmail(recipients=email, sender=None, subject=subject, message=message)
			except:
				pass

	def set_dsa_rate(self):
		if self.grade:
			self.db_set("dsa_per_day", frappe.db.get_value("Employee Grade", self.grade, "dsa"))

	@frappe.whitelist()
	def set_estimate_amount(self):
		total_days = 0.0
		dsa_rate  = frappe.db.get_value("Employee Grade", self.grade, "dsa")
		if not dsa_rate:
			frappe.throw("No DSA Rate set for Grade <b> {0} /<b> ".format(self.grade))
		return_dsa = frappe.get_doc("HR Settings").return_day_dsa
		if not return_dsa:
			frappe.throw("Set Return Day DSA Percent in HR Settings")
		return_day = 1
		full_dsa = half_dsa = 0
		for i in self.items:
			from_date = i.date
			to_date   = i.date if not i.till_date else i.till_date
			no_days   = date_diff(to_date, from_date) + 1
			# if i.quarantine:
			# 	no_days = 0
			total_days  += no_days
			# frappe.msgprint("{0} {1}".format(from_date, total_days))
		if flt(total_days) <= 15:
			full_dsa = flt(total_days) - flt(return_day) 
			half_dsa = 0.0

		elif 15 < flt(total_days) <= 30:
			full_dsa = 15
			half_dsa = flt(total_days) -15 - flt(return_day)

		elif flt(total_days) > 30:
			full_dsa = 15
			half_dsa = 15  - flt(return_day)

		self.estimated_amount = (flt(full_dsa) * flt(dsa_rate)) + (flt(half_dsa) * 0.5 * flt(dsa_rate)) + flt(return_day) * (flt(return_dsa)/100)* flt(dsa_rate) 
	@frappe.whitelist()
	def check_double_dates(self):
		pass
		# for i in self.get('items'):
		# 	for j in self.get('items'):
		# 		if i.name != j.name and str(i.date) <= str(j.till_date) and str(i.till_date) >= str(j.date):
		# 			frappe.throw(_("Row#{}: Dates are overlapping with Row#{}").format(i.idx, j.idx))

@frappe.whitelist()
def make_travel_claim(source_name, target_doc=None): 
	def update_date(obj, target, source_parent):
		target.posting_date = nowdate()
		target.supervisor = None
		# target.for_maintenance_project = 1

	def transfer_currency(obj, target, source_parent):
		if obj.halt:
			target.from_place = None
			target.to_place = None
		else:
			target.no_days = 1
			target.halt_at = None
		target.currency = source_parent.currency
		target.currency_exchange_date = source_parent.posting_date
		target.dsa = source_parent.dsa_per_day
		if target.currency == "BTN":
			target.exchange_rate = 1
		else:
			target.exchange_rate = get_exchange_rate(target.currency, "BTN", date=source_parent.posting_date)
		target.amount = target.dsa
		if target.halt:
			target.amount = flt(target.dsa) * flt(target.no_days)
		target.actual_amount = target.amount * target.exchange_rate

	def adjust_last_date(source, target):
		dsa_percent = frappe.db.get_single_value("HR Settings", "return_day_dsa")
		percent = flt(dsa_percent) / 100.0
		target.items[len(target.items) - 1].dsa_percent = dsa_percent
		target.items[len(target.items) - 1].actual_amount = target.items[len(target.items) - 1].actual_amount * percent
		target.items[len(target.items) - 1].amount = target.items[len(target.items) - 1].amount * percent
		target.items[len(target.items) - 1].last_day = 1 

	doc = get_mapped_doc("Travel Authorization", source_name, {
			"Travel Authorization": {
				"doctype": "Travel Claim",
				"field_map": {
					"name": "ta",
					"posting_date": "ta_date",
					"advance_amount_nu": "advance_amount"
				},
				"postprocess": update_date,
				"validation": {"docstatus": ["=", 1]}
			},
			"Travel Authorization Item": {
				"doctype": "Travel Claim Item",
				"postprocess": transfer_currency,
				"travel_authorization": "parent"
			},
		}, target_doc, adjust_last_date)
	return doc

@frappe.whitelist()
def get_exchange_rate(from_currency, to_currency, date=None):
	# Following line is replaced by subsequent code by SHIV on 2020/09/22
	#ex_rate = frappe.db.get_value("Currency Exchange", {"from_currency": from_currency, "to_currency": to_currency}, "exchange_rate")
	if not date or date == "" or date == " ":
		frappe.throw("Please select Currency Exchange Date.")
	ex_rate = frappe.db.sql("""select exchange_rate 
					from `tabCurrency Exchange`
					where from_currency = '{from_currency}'
					and to_currency = '{to_currency}'
					and `date` = '{data}'
					order by `date` desc
					limit 1
	""".format(from_currency=from_currency, to_currency=to_currency, data=date), as_dict=False)
	if not ex_rate:
		frappe.throw("No Exchange Rate defined in Currency Exchange for the date {}! Kindly contact your accounts section".format(date))
	else:
		return ex_rate[0][0]

# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabTravel Authorization`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabTravel Authorization`.employee
				and `tabEmployee`.user_id = '{user}' and `tabTravel Authorization`.docstatus != 2)
		or
		exists(select 1
				from `tabEmployee`, `tabHas Role`
				where `tabEmployee`.user_id = `tabHas Role`.parent
				and `tabHas Role`.role = 'Travel Administrator'
				and (select region from `tabEmployee` where `tabEmployee`.name = `tabTravel Authorization`.employee limit 1) = (select region from `tabEmployee` where `tabEmployee`.user_id = '{user}' limit 1)
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabTravel Authorization`.supervisor = '{user}' and `tabTravel Authorization`.workflow_state not in ('Draft','Approved','Rejected','Rejected By Supervisor','Cancelled'))
		or 
		(`tabTravel Authorization`.supervisor_manager = '{user}' and `tabTravel Authorization`.workflow_state not in ('Draft', 'Rejected', 'Cancelled','Approved','Rejected By Supervisor'))
	)""".format(user=user)

# @frappe.whitelist()
# def update_date_authorization(idIdx, auth_date, ta_id):
# 	frappe.db.sql("update `tabTravel Authorization Item` set date='{}' where idx= '{}' and parent='{}'".format(auth_date, idIdx, ta_id))
