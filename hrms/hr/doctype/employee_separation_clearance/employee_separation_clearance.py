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
		self.check_document_no()
		self.update_reference()
		self.notify_employee()

	def on_cancel(self):
		self.update_reference()
		self.notifiy_employee()

	def check_document_no(self):
		if not self.document_no:
			frappe.throw("Document No. missing. Please contact HR.")

	def check_signatures(self):
		if self.director_clearance == 0:
			frappe.throw("Director (SLD) has not granted clearance.")
		if self.hrad_clearance == 0:
			frappe.throw("General Manager (HRAD) has not granted clearance.")
		if self.gmod_clearance == 0:
			frappe.throw("General Manager (Operation Division) has not granted clearance.")
		if self.gmpd_clearance == 0:
			frappe.throw("General Manager (Project Division) has not granted clearance.")

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
	
	@frappe.whitelist()
	def check_logged_in_user_role(self):
		#return values initialization-----------------
		display = 1
		director = 1
		hrad = 1
		gmod = 1
		gmpd = 1

		#----------------------------Director, SLD------------------------------------------------------------------------------------------------------------------------------------------------------------|
		director_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "dsld"))
		if frappe.session.user == frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "dsld"),"user_id"):
			director = 0
		if director_officiate and frappe.session.user == frappe.db.get_value("Employee",director_officiate[0].officiate,"user_id"):
			director = 0
		#----------------------------GM, Operation Division -----------------------------------------------------------------------------------------------------------------------------------------------------|
		gmod_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "gm_operation_division"))
		if frappe.session.user == frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "gm_operation_division"),"user_id"):
			gmod = 0
		if gmod_officiate and frappe.session.user == frappe.db.get_value("Employee",gmod_officiate[0].officiate,"user_id"):
			gmod = 0
		#----------------------------GM, HRAD -----------------------------------------------------------------------------------------------------------------------------------------------------|
		hrad_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "gm_hrad"))
		if frappe.session.user == frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "gm_hrad"),"user_id"):
			hrad = 0
		if hrad_officiate and frappe.session.user == frappe.db.get_value("Employee",hrad_officiate[0].officiate,"user_id"):
			hrad = 0
		#----------------------------GM, Project Division -----------------------------------------------------------------------------------------------------------------------------------------------------|
		gmpd_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "gm_project_division"))
		if frappe.session.user == frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "gm_project_division"),"user_id"):
			gmpd = 0
		if gmpd_officiate and frappe.session.user == frappe.db.get_value("Employee",gmpd_officiate[0].officiate,"user_id"):
			gmpd = 0
		return director, hrad, gmpd, gmod

	def get_receipients(self):
		receipients = []
		if self.director:
			receipients.append(self.director)
		if self.hrad:
			receipients.append(self.hrad)
		if self.gmod:
			receipients.append(self.gmod)
		if self.gmpd:
			receipients.append(self.gmpd)
		# if self.hr:
		# 	receipients.append(self.hr)

		return receipients

	def notify_approvers(self):
		parent_doc = frappe.get_doc(self.doctype, self.name)
		args = parent_doc.as_dict()
		receipients = []
		receipients = self.get_receipients()
		template = frappe.db.get_single_value('HR Settings', 'employee_separation_clearance_approval_notification_template')
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
		template = frappe.db.get_single_value('HR Settings', 'employee_separation_clearance_status_notification_template')
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
		#----------------------------Director, SLD-----------------------------------------------------------------------------------------------------------------------------------------------------------|
		director_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "dsld"))
		if director_officiate:
			self.director = frappe.db.get_value("Employee",director_officiate[0].officiate,"user_id")
		else:
			self.director = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "dsld"),"user_id")
		#--------------------------- GM, HRAD-----------------------------------------------------------------------------------------------------------------------------------------------------|
		gmod_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "dsld"))
		if gmod_officiate:
			self.gmod = frappe.db.get_value("Employee",gmod_officiate[0].officiate,"user_id")
		else:
			self.gmod = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "gm_operation_division"),"user_id")
		#--------------------------- GM, Operation Division-----------------------------------------------------------------------------------------------------------------------------------------------------|
		hrad_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "gm_hrad"))
		if hrad_officiate:
			self.hrad = frappe.db.get_value("Employee",hrad_officiate[0].officiate,"user_id")
		else:
			self.hrad = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "gm_hrad"),"user_id")
		#--------------------------- GM, Project Division-----------------------------------------------------------------------------------------------------------------------------------------------------|
		gmpd_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "gm_project_division"))
		if gmpd_officiate:
			self.gmpd = frappe.db.get_value("Employee",gmpd_officiate[0].officiate,"user_id")
		else:
			self.gmpd = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "gm_project_division"),"user_id")

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
		(`tabEmployee Separation Clearance`.director = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.hrad = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.gmpd = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.gmod = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)

	)""".format(user=user)