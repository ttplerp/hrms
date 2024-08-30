# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document

from hrms.hr.utils import validate_active_employee
import frappe
from frappe import _
from frappe.utils.data import add_days
from frappe.query_builder.functions import Sum
from frappe.utils import date_diff, flt, cint, nowdate
from erpnext.accounts.doctype.accounts_settings.accounts_settings import get_bank_account
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from datetime import datetime

class TravelRequest(AccountsController):
	def validate(self):
		validate_workflow_states(self)
		validate_active_employee(self.employee)
		self.validate_travel_dates()
		self.check_leave_applications()
		self.set_dsa_percent()
		self.set_currency_exchange()
		self.update_amount()
		self.update_total_amount()
		self.validate_advance_amount()
		if self.workflow_state == "Verified By Supervisor":
			self.notify_supervisor()
		if self.workflow_state == "Waiting Supervisor Approval":
			self.check_advance_and_report()
			self.notify_supervisor()
		if self.workflow_state != "Approved":
			notify_workflow_states(self)
		if self.training_event:
			self.update_training_event()

	def on_update(self):
		self.validate_travel_dates(update=True)
		self.check_leave_applications()
		self.check_date_overlap()
		self.check_duplicate_requests()
		
	def on_submit(self):
		self.check_date()
		self.make_employee_advance()
		self.post_expense_claim()
		notify_workflow_states(self)

	def on_cancel(self):
		notify_workflow_states(self)
		self.update_training_event(cancel=True)

	def on_trash(self):
		self.update_training_event(cancel=True)

	def validate_advance_amount(self):
		if flt(self.advance_amount) > flt(self.total_travel_amount) * flt(0.75):
			frappe.msgprint("Advance amount cannot be greater than 75% of the <b>Total Travel Amount</b>",title="Excess Advance Amount",indicator="red",raise_exception=True)
		elif flt(self.advance_amount) <= 0 and self.need_advance == 1:
			frappe.throw("Advance amount cannot be: {}".format(self.advance_amount))

	def update_training_event(self, cancel = False):
		if not cancel:
			if frappe.db.get_value("Training Event Employee", self.training_event_child_ref, "travel_request_id") in (None, ''):
				frappe.db.sql("""
					update `tabTraining Event Employee` set travel_request_id = '{}' where name = '{}'
					""".format(self.name, self.training_event_child_ref))
		else:
			if frappe.db.get_value("Training Event Employee", self.training_event_child_ref, "travel_request_id") == self.name:
				frappe.db.sql("""
					update `tabTraining Event Employee` set travel_request_id = NULL where name = '{}'
					""".format(self.training_event_child_ref))
	def set_dsa_percent(self):
		for item in self.get("itinerary"):
			if len(self.itinerary) == 1 or item.idx == len(self.itinerary) or cint(item.return_same_day) == 1:
				item.dsa_percent = cint(frappe.db.get_single_value("HR Settings","returen_day_dsa_percent"))
				if self.travel_type == "International" and flt(item.total_claim) <=0:
					item.actual_amount = 0

	##
	# Check if the dates are used under Leave Application
	##
	def check_leave_applications(self):
		las = frappe.db.sql("""select t1.name from `tabLeave Application` t1 
				where t1.employee = "{employee}"
				and t1.docstatus != 2
				and exists(select 1
						from `tabTravel Itinerary` t2
						where t2.parent = "{travel_authorization}"
      					and (t2.from_date between t1.from_date and t1.to_date) or (t2.to_date between t1.from_date and t1.to_date)
						)
		""".format(travel_authorization = self.name, employee = self.employee), as_dict=True)
		for t in las:
			frappe.throw("The dates in your current travel request have been used in leave application {}".format(frappe.get_desk_link("Leave Application", t.name)))

	def check_advance_and_report(self):
		if self.need_advance == 1:
			if (self.employee_advance_reference and not frappe.db.exists("Employee Advance", self.employee_advance_reference)) or not self.employee_advance_reference:
				self.db_set("employee_advance_reference",None)
				frappe.db.commit()
			else:
				if frappe.db.get_value("Employee Advance",self.employee_advance_reference,"status") != "Paid":
					frappe.throw("Cannot Apply whithout claiming travel advance")
		if not self.attach_report:
			frappe.throw("Tour Report is mandatory")
	
	def update_total_amount(self):
		total = 0
		base_total = 0

		for item in self.get("itinerary"):
			if self.travel_type == "Domestic":
				total += float(item.total_claim)
				base_total += float(item.actual_amount) if item.actual_amount else item.amount
				base_total += float(item.mileage_amount) if item.mileage_amount else 0
				base_total += float(item.fare_amount) if item.fare_amount else 0
				base_total += float(item.entertainment_amount) if item.entertainment_amount and item.ea_applicable == 1 else 0
				base_total += float(item.hotel_charges_amount) if item.hotel_charges_amount and item.hc_applicable == 1 else 0
			else:
				total = flt(total)+flt(item.actual_amount)
				base_total += float(item.actual_amount) if item.actual_amount else item.amount
		self.total_travel_amount = total
		self.base_total_travel_amount = base_total
		self.balance_amount = flt(self.total_travel_amount) - flt(self.advance_amount)
		self.base_balance_amount = flt(self.base_total_travel_amount) - flt(self.advance_amount_nu)

	def set_currency_exchange(self):
		for item in self.get("itinerary"):
			if not item.total_claim:
				item.total_claim = 0
			if item.currency != "BTN":
				to_currency = "BTN"
				from_currency = item.currency
				posting_date = item.from_date
				exchange_rate = get_exchange_rate(from_currency, to_currency, posting_date)
				item.actual_amount = float(item.total_claim) * float(exchange_rate)
			elif self.travel_type == "International":
				item.actual_amount = float(item.total_claim)

	def check_date(self):
		for item in self.get("itinerary"):
			las_date = item.from_date
		if datetime.strptime(nowdate(),"%Y-%m-%d").date() <= datetime.strptime(str(las_date),"%Y-%m-%d").date():
			frappe.throw("Cannot Claim Travel before '{}'".format(las_date))

	def check_duplicate_requests(self):
		# check if the travel dates are already used in other travel request
		tas = frappe.db.sql("""select t3.idx, t1.name, t2.from_date, t2.to_date
				from 
					`tabTravel Request` t1, 
					`tabTravel Itinerary` t2,
					`tabTravel Itinerary` t3
				where t1.employee = "{employee}"
				and t1.docstatus != 2
				and t1.workflow_state !="Rejected"
				and t1.name != "{name}"
				and t2.parent = t1.name
				and t3.parent = "{name}"
				and (
					(t2.from_date <= t3.to_date and t2.to_date >= t3.from_date)
					or
					(t3.from_date <= t2.to_date and t3.to_date >= t2.from_date)
				)
		""".format(name = self.name, employee = self.employee), as_dict=True)
		for t in tas:
			frappe.throw("Row#{}: Dates in this request are overlapping with other {} between {} and {}"\
				.format(t.idx, frappe.get_desk_link("Travel Request", t.name), t.from_date, t.to_date))

	def check_date_overlap(self):
		overlap = frappe.db.sql("""select t1.idx, 
				ifnull((select t2.idx from `tabTravel Itinerary` t2
					where t2.parent = t1.parent
					and t2.name != t1.name
					and t1.from_date <= t2.to_date and t1.to_date >= t2.from_date
					limit 1),-1) overlap_idx
			from `tabTravel Itinerary` t1
			where t1.parent = "{parent}"
			order by t1.from_date""".format(parent = self.name), as_dict=True)
			
		for d in overlap:
			if d.overlap_idx >= 0:
				frappe.throw(_("Row#{}: Dates are overlapping with dates in Row#{}").format(d.idx, d.overlap_idx))
	
	def validate_travel_dates(self, update=False):
		for item in self.get("itinerary"):
			if cint(item.halt):
				if not item.halt_at:
					frappe.throw(_("Row#{}: <b>Halt at</b> is mandatory").format(item.idx))
				elif not item.to_date:
					frappe.throw(_("Row#{0}: <b>Till Date</b> is mandatory").format(item.idx),title="Invalid Date")
				elif item.from_date and item.to_date and (item.to_date < item.from_date):	
					frappe.throw(_("Row#{0}: <b>Till Date</b> cannot be earlier to <b>From Date</b>").format(item.idx),title="Invalid Date")
			else:
				if not (item.travel_from and item.travel_to):
					frappe.throw(_("Row#{0}: <b>Travel From</b> and <b>Travel To</b> are mandatory").format(item.idx))
				item.to_date = item.from_date
			from_date = item.from_date
			to_date   = item.from_date if not item.to_date else item.to_date
			item.no_days   = date_diff(to_date, from_date) + 1
			if update:
				frappe.db.set_value("Travel Itinerary", item.name, "no_days", item.no_days)
		if self.itinerary:
			# check if the travel dates are already used in other travel authorization
			tas = frappe.db.sql("""select t3.idx, t1.name, t2.from_date, t2.to_date
					from 
						`tabTravel Request` t1, 
						`tabTravel Itinerary` t2,
						`tabTravel Itinerary` t3
					where t1.employee = "{employee}"
					and t1.docstatus != 2
					and t1.workflow_state !="Rejected"
					and t1.name != "{travel_authorization}"
					and t2.parent = t1.name
					and t3.parent = "{travel_authorization}"
					and (
						(t2.from_date <= t3.to_date and t2.to_date >= t3.from_date)
						or
						(t3.from_date <= t2.to_date and t3.to_date >= t2.from_date)
					)
			""".format(travel_authorization = self.name, employee = self.employee), as_dict=True)
			for t in tas:
				frappe.throw("Row#{}: The dates in your current Travel Request have already been claimed in {} between {} and {}"\
					.format(t.idx, frappe.get_desk_link("Travel Request", t.name), t.from_date, t.to_date))
	
	
	def update_amount(self):
		company_currency = "BTN"
		for item in self.get("itinerary"):
			visa_exchange_rate  = 1 if item.visa_fees_currency == company_currency else get_exchange_rate(item.visa_fees_currency, company_currency, item.currency_exchange_date)
			passport_exchange_rate  = 1 if item.passport_fees_currency == company_currency else get_exchange_rate(item.passport_fees_currency, company_currency, item.currency_exchange_date)
			incidental_exchange_rate  = 1 if item.incidental_fees_currency == company_currency else get_exchange_rate(item.incidental_fees_currency, company_currency, item.currency_exchange_date)
			if not item.to_date:
				item.no_days_actual = date_diff(item.from_date, item.from_date)+1
			else:
				item.no_days_actual = date_diff(item.to_date, item.from_date)+1
			item.amount = flt(item.no_days_actual) * (flt(item.dsa) * (flt(item.dsa_percent)/100))
			item.mileage_amount = flt(item.mileage_rate) * flt(item.distance)
			item.mileage_amount = flt(item.mileage_amount)
			item.total_claim = flt(item.amount)+flt(item.mileage_amount)+flt(item.fare_amount)+flt(item.entertainment_amount)+flt(item.hotel_charges_amount) + flt(item.visa_fees) * flt(visa_exchange_rate) + flt(item.passport_fees) * flt(passport_exchange_rate) + flt(item.incidental_fees) * flt(incidental_exchange_rate)
			if self.travel_type == "Domestic":
				item.total_claim += flt(item.porter_pony_charges)

	def make_employee_advance(self):
		if cint(self.need_advance) and flt(self.advance_amount) > 0:
			self.make_advance_payment()

	@frappe.whitelist()
	def make_advance_payment(self):
		default_employee_advance_account = frappe.get_value("Company", self.company, "travel_advance_account")
		doc = frappe.new_doc("Employee Advance")
		doc.reference_type 	= self.doctype
		doc.reference 		= self.name
		doc.employee 		= self.employee
		doc.branch 			= self.branch
		doc.posting_date 	= self.posting_date
		doc.currency 		= self.currency
		doc.advance_type   	="Travel Advance"
		doc.purpose 		= "Travel Advance {}".format(self.name)
		doc.advance_amount 	= self.advance_amount
		doc.claimed_amount 	= 0
		doc.pending_amount 	= self.advance_amount
		doc.paid_amount 	= 0
		doc.return_amount 	= 0
		doc.exchange_rate 	= 1
		doc.advance_account = default_employee_advance_account
		return doc
	
	def post_expense_claim(self):
		default_payable_account = frappe.get_cached_value("Company", self.company, "default_expense_claim_payable_account")
		default_cost_center = frappe.get_cached_value("Company", self.company, "cost_center")
		expense_claim = frappe.new_doc("Expense Claim")
		expense_claim.flags.ignore_mandatory = True
		expense_claim.company = self.company
		expense_claim.employee = self.employee
		expense_claim.payable_account = default_payable_account
		expense_claim.cost_center = self.cost_center or default_cost_center
		expense_claim.is_paid = 0
		expense_claim.expense_approver = frappe.db.get_value('Employee', self.employee, 'expense_approver')
		expense_claim.branch = self.branch
		
		if self.travel_type == "Domestic":
			if self.purpose_of_travel == "Meeting & Seminars":
				default_account = frappe.db.get_value("Company", self.company, "meeting_and_seminars_incountry_account")
			elif self.purpose_of_travel == "Training":
				default_account = frappe.db.get_value("Company", self.company, "training_in_country_account")
		else:
			if self.purpose_of_travel == "Meeting & Seminars":
				default_account = frappe.db.get_value("Company", self.company, "meeting_and_seminars_outcountry_account")
			elif self.purpose_of_travel == "Training":
				default_account = frappe.db.get_value("Company", self.company, "training_out_country_account")
		
		travel_amt = mileage_amt = hotel_amt = entertainment_amt = fare_amt = 0
		
		for d in self.get("itinerary"):
			if self.travel_type == "Domestic":
				travel_amt += d.amount
				mileage_amt += d.mileage_amount
				hotel_amt += d.hotel_charges_amount
				entertainment_amt += d.entertainment_amount
				fare_amt += d.fare_amount
			else:
				exchange_rate = float(d.exchange_rate) if d.currency != "BTN" else 1.0
				travel_amt += float(d.amount) * exchange_rate
				mileage_amt += float(d.mileage_amount) * exchange_rate
				hotel_amt += float(d.hotel_charges_amount) * exchange_rate
				entertainment_amt += float(d.entertainment_amount) * exchange_rate
				fare_amt += float(d.fare_amount) * exchange_rate
		
		expense_types = [
			("Travel (In Country)" if self.travel_type == "Domestic" else "Travel (Ex Country)", travel_amt-self.advance_amount),
			("Mileage (In Country)" if self.travel_type == "Domestic" else "Mileage (In Country)", mileage_amt),
			("Accommodation Expense (In country)" if self.travel_type == "Domestic" else "Accommodation Expense (Ex country)", hotel_amt),
			("Entertainment Expense (In Country)" if self.travel_type == "Domestic" else "Entertainment Expense (Ex Country)", entertainment_amt),
			("Transportation Expense (In Country)" if self.travel_type == "Domestic" else "Transportation Expense (Ex Country)", fare_amt)
		]
		
		for expense_type, amount in expense_types:
			if amount > 0:
				expense_claim.append('expenses', {
					"expense_date": nowdate(),
					"expense_type": expense_type,
					"amount": amount,
					"sanctioned_amount": amount,
					"reference_type": self.doctype,
					"reference": self.name,
					"cost_center": self.cost_center or default_cost_center
				})

		for advance in self.get_advances():
			expense_claim.append(
				"advances",
				{
					"employee_advance": advance.name,
					"posting_date":		advance.posting_date,
					"advance_paid": 	flt(advance.paid_amount),
					"unclaimed_amount": flt(advance.paid_amount) - flt(advance.claimed_amount),
					"allocated_amount": flt(advance.paid_amount) - flt(advance.claimed_amount),
					"advance_account" : advance.advance_account
				})
			
		expense_claim.save(ignore_permissions=True)
		# expense_claim.submit()
		frappe.msgprint(
			_("Expense Claim record {0} created")
			.format("<a href='/app/Form/Expense Claim/{0}'>{0}</a>")
			.format(expense_claim.name))

	# pull advances if exists against travel request	
	def get_advances(self):
		advance = frappe.qb.DocType("Employee Advance")

		query = frappe.qb.from_(advance).select(
			advance.name,
			advance.posting_date,
			advance.paid_amount,
			advance.pending_amount,
			advance.advance_account,
		).where(
			(advance.docstatus == 1)
			& (advance.employee == self.employee)
			& (advance.paid_amount > 0)
			& (advance.status.notin(["Claimed", "Returned", "Partly Claimed and Returned"]))
			& (advance.reference_type == self.doctype)
			& (advance.reference == self.name)
		)
		return query.run(as_dict=True)
	
	def notify_supervisor(self):
		division = frappe.db.get_value("Employee",self.employee,"division")
		supervisor = frappe.db.get_value("Employee", frappe.db.get_value("Department",division,"approver"),"user_id")
		if not supervisor:
			frappe.throw("Set employee Supervisor for employee {}".format(self.employee))
		parent_doc = frappe.get_doc(self.doctype, self.name)
		args = parent_doc.as_dict()
		template = frappe.db.get_single_value('HR Settings', 'travel_request_supervisor_notification_template')
		if not template:
			frappe.msgprint(_("Please set default template for Travel Request Supervisor Notification in HR Settings."))
			return
		email_template = frappe.get_doc("Email Template", template)
		message = frappe.render_template(email_template.response, args)

		self.notify({
			# for post in messages
			"message": message,
			"message_to": supervisor,
			# for email
			"subject": email_template.subject,
			"notify": "supervisor"
		})

	def notify(self, args, approver = 0):
		args = frappe._dict(args)
		# args -> message, message_to, subject

		contact = args.message_to
		if not isinstance(contact, list):
			if not args.notify == "supervisor":
				contact = frappe.get_doc('User', contact).email or contact

		sender      	    = dict()
		sender['email']     = frappe.get_doc('User', frappe.session.user).email
		sender['full_name'] = frappe.utils.get_fullname(sender['email'])

		try:
			frappe.sendmail(
				recipients = contact,
				sender = sender['email'],
				subject = args.subject,
				message = args.message,
			)
			if approver == 0:
				frappe.msgprint(_("Email sent to {0}").format(contact))
			else:
				return _("Email sent to {0}").format(contact)
		except frappe.OutgoingEmailError:
			pass


@frappe.whitelist()
def get_exchange_rate(from_currency, to_currency, posting_date):
	if not posting_date:
		frappe.msgprint("Please select Date")
	ex_rate = frappe.db.sql("""select exchange_rate 
		from `tabCurrency Exchange`
		where from_currency = '{from_currency}'
		and to_currency = '{to_currency}'
		and date = '{posting_date}'
		order by date desc
		limit 1
	""".format(from_currency=from_currency, to_currency=to_currency, posting_date=posting_date), as_dict=True)
	if not ex_rate:
		if from_currency == "BTN":
			return 1
		frappe.throw("No Exchange Rate defined in Currency Exchange! Kindly contact your accounts section")
	else:
		return ex_rate[0].exchange_rate
	

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabTravel Request`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabTravel Request`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabTravel Request`.supervisor = '{user}' and `tabTravel Request`.workflow_state not in  ('Draft','Approved','Rejected','Cancelled'))
	)""".format(user=user)