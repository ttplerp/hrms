# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from hrms.hr.hr_custom_functions import get_officiating_employee

class EmployeeSeparationClearance(Document):
	def validate(self):
		# validate_workflow_states(self)
		self.check_duplicates()
		self.check_reference()
		if self.approvers_set == 0:
			self.set_approvers()

	@frappe.whitelist()
	def apply(self):
		if self.mail_sent == 0:
			msg = self.notify_approvers()
		# notify_workflow_states(self)
		return msg

	def on_submit(self):
		self.check_signatures()
		self.update_reference()
		self.notify_employee()

	def on_cancel(self):
		self.update_reference()
		self.notifiy_employee()

	def check_signatures(self):
		if self.supervisor_clearance == 0:
			frappe.throw("Supervisor has not granted clearance.")
		if self.afd_clearance == 0:
			frappe.throw("Accounts & Finance Division has not granted clearance.")
		if self.ceo_clearance == 0:
			frappe.throw("CEO has not granted clearance.")
		if self.icthr_clearance == 0:
			frappe.throw("HR Division has not granted clearance.")
		if self.iad_clearance == 0:
			frappe.throw("Internal Audit Division has not granted clearance.")
		if self.rtc_clearance == 0:
			frappe.throw("Rental and Tenancy has not granted clearance.")
		if self.clearance == 0:
			frappe.throw("ICT Division has not granted clearance.")
		# if self.sws_clearance == 0:
		# 	frappe.throw("SWS Treasurer has not granted clearance.")

	def update_reference(self):
		id = frappe.get_doc("Employee Separation",self.employee_separation_id)
		id.clearance_acquired = 1 if self.docstatus == 1 else 0
		id.save()

	def check_reference(self):
		if not self.employee_separation_id:
			frappe.throw("Employee Separation Clearance creation should route through Employee Separation Document.",title="Cannot Save")

	def check_duplicates(self):
		duplicates = frappe.db.sql("""
            select name from `tabEmployee Separation Clearance` where employee_separation_id = '{0}'  and name != '{1}' and docstatus != 2
                """.format(self.employee_separation_id,self.name))
		if duplicates:
			frappe.throw("There is already a pending Separation Clearance created for the Employee Separation '{}'".format(self.employee_separation_id))
	
	def get_receipients(self):
		receipients = []
		if self.supervisor:
			receipients.append(self.supervisor)
		if self.afd:
			receipients.append(self.afd)
		if self.ceo:
			receipients.append(self.ceo)
		if self.icthr:
			receipients.append(self.icthr)
		if self.iad:
			receipients.append(self.iad)
		if self.rtc:
			receipients.append(self.rtc)
		if self.ict:
			receipients.append(self.ict)
		# if self.sws:
		# 	receipients.append(self.sws)

		return receipients

	def notify_approvers(self):
		parent_doc = frappe.get_doc(self.doctype, self.name)
		args = parent_doc.as_dict()
		receipients = []
		receipients = self.get_receipients()
		template = frappe.db.get_single_value('HR Settings', 'employee_separation_approval_notification_template')
		if not template:
			frappe.msgprint(_("Please set default template for Employee Separation Clearance Notification in HR Settings."))
			return 
		email_template = frappe.get_doc("Email Template", template)
		message = frappe.render_template(email_template.response, args)
		msg = self.notify({
			# for post in messages
			"message": message,
			"message_to": receipients,
			# for email
			"subject": email_template.subject
		},1)
		if msg != "Failed":
			self.db_set("mail_sent",1)
		return str(msg)

	def notify_employee(self):
		employee = frappe.get_doc("Employee", self.employee)
		if not employee.user_id:
			return
		parent_doc = frappe.get_doc(self.doctype, self.name)
		args = parent_doc.as_dict()
		template = frappe.db.get_single_value('HR Settings', 'employee_separation_status_notification_template')
		if not template:
			frappe.msgprint(_("Please set default template for Employee Separation Clearance Status Notification in HR Settings."))
			return
		email_template = frappe.get_doc("Email Template", template)
		message = frappe.render_template(email_template.response, args)

		self.notify({
			# for post in messages
			"message": message,
			"message_to": employee.user_id,
			# for email
			"subject": email_template.subject,
			"notify": "employee"
		})

	def notify(self, args, approver = 0):
		args = frappe._dict(args)
		# args -> message, message_to, subject

		contact = args.message_to
		if not isinstance(contact, list):
			if not args.notify == "employee":
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
	def set_approvers(self):
		#----------------------------Supervisor-----------------------------------------------------------------------------------------------------------------------------------------------------------|
		if not frappe.db.get_value("Employee",self.employee, "reports_to"):
			frappe.throw("Reports To for employee {} is not set".format(self.employee))
		supervisor_officiate = get_officiating_employee(frappe.db.get_value("Employee",self.employee, "reports_to"))
		if supervisor_officiate:
			self.supervisor = frappe.db.get_value("Employee",supervisor_officiate[0].officiate,"user_id")
		else:
			self.supervisor = frappe.db.get_value("Employee",frappe.db.get_value("Employee",self.employee, "reports_to"),"user_id")
		#--------------------------- Accounts & Finance Division-----------------------------------------------------------------------------------------------------------------------------------------------------|
		if not frappe.db.get_single_value("HR Settings", "afd"):
			frappe.throw("Accounts & Finance Division clearance approver is not set in HR Settings")
		afd_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "afd"))
		if afd_officiate:
			self.afd = frappe.db.get_value("Employee",afd_officiate[0].officiate,"user_id")
		else:
			self.afd = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "afd"),"user_id")
		#--------------------------- CEO -----------------------------------------------------------------------------------------------------------------------------------------------------|
		ceo_officiate = get_officiating_employee(frappe.db.get_value("Employee", {"designation": "Chief Executive Officer", "status": "Active"}, "name"))
		# if not frappe.db.get_value("Employee", {"designation": "Chief Executive Officer", "status": "Active"}, "name"):
		# 	frappe.throw("Store & Procurement Division clearance approver is not set in HR Settings")
		if ceo_officiate:
			self.ceo = frappe.db.get_value("Employee",ceo_officiate[0].officiate,"user_id")
		else:
			self.ceo = frappe.db.get_value("Employee", {"designation": "Chief Executive Officer", "status": "Active"}, "user_id")
		#--------------------------- Store & Procurement Division-----------------------------------------------------------------------------------------------------------------------------------------------------|
		# spd_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "spd"))
		# if not frappe.db.get_single_value("HR Settings", "spd"):
		# 	frappe.throw("Store & Procurement Division clearance approver is not set in HR Settings")
		# if spd_officiate:
		# 	self.spd = frappe.db.get_value("Employee",spd_officiate[0].officiate,"user_id")
		# else:
		# 	self.spd = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "spd"),"user_id")
		#--------------------------- ICT & HR Division-----------------------------------------------------------------------------------------------------------------------------------------------------|
		if not frappe.db.get_single_value("HR Settings", "icthr"):
			frappe.throw("ICT & HR Division clearance approver is not set in HR Settings")
		icthr_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "icthr"))
		if icthr_officiate:
			self.icthr = frappe.db.get_value("Employee",icthr_officiate[0].officiate,"user_id")
		else:
			self.icthr = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "icthr"),"user_id")

		#--------------------------- Internal Audit Division-----------------------------------------------------------------------------------------------------------------------------------------------------|
		if not frappe.db.get_single_value("HR Settings", "iad"):
			frappe.throw("Internal Audit Division clearance approver is not set in HR Settings")
		iad_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "iad"))
		if iad_officiate:
			self.iad = frappe.db.get_value("Employee",iad_officiate[0].officiate,"user_id")
		else:
			self.iad = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "iad"),"user_id")
		
		#--------------------------- Rental and Tenancy-----------------------------------------------------------------------------------------------------------------------------------------------------|
		if not frappe.db.get_single_value("HR Settings", "rtc"):
			frappe.throw("Rental and Tenacy clearance approver is not set in HR Settings")
		rtc_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "rtc"))
		if rtc_officiate:
			self.rtc = frappe.db.get_value("Employee",rtc_officiate[0].officiate,"user_id")
		else:
			self.rtc = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "rtc"),"user_id")
		
		#--------------------------- ICT Division-----------------------------------------------------------------------------------------------------------------------------------------------------|
		if not frappe.db.get_single_value("HR Settings", "ict"):
			frappe.throw("ICT Division clearance approver is not set in HR Settings")
		ict_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "ict"))
		if ict_officiate:
			self.ict = frappe.db.get_value("Employee",ict_officiate[0].officiate,"user_id")
		else:
			self.ict = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "ict"),"user_id")
		#--------------------------- SWS Treasurer-----------------------------------------------------------------------------------------------------------------------------------------------------|
		# sws_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "ict"))
		# if sws_officiate:
		# 	self.sws = frappe.db.get_value("Employee",sws_officiate[0].officiate,"user_id")
		# else:
		# 	self.sws = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "sws"),"user_id")

		self.db_set("approvers_set",1)

# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabEmployee Separation Clearance`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabEmployee Separation Clearance`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabEmployee Separation Clearance`.supervisor = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.afd = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.ceo = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.icthr = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.iad = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.rtc = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.ict = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)

	)""".format(user=user)