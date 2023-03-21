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
		self.check_duplicates()
		self.check_reference()
		if self.approvers_set == 0:
			self.set_approvers()

	@frappe.whitelist()
	def apply(self):
		if self.mail_sent == 0:
			msg = self.notify_approvers()
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
		if self.fa_clearance == 0:
			frappe.throw("Finance Section (Approver) has not granted clearance.")
		if self.ita_clearance == 0:
			frappe.throw("IT Section (Approver) has not granted clearance.")
		if self.iaa_clearance == 0:
			frappe.throw("Internal Audit (Approver) has not granted clearance.")
		if self.hsa_clearance == 0:
			frappe.throw("Home Store (Approver) has not granted clearance.")

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
		fa = 1
		ita = 1
		iaa = 1
		hsa = 1

		#----------------------------Finance Section Approver-----------------------------------------------------------------------------------------------------------------------------------------------------------|
		finance_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "fsa"))
		if frappe.session.user == frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "fsa"),"user_id"):
			fa = 0
		if finance_officiate and frappe.session.user == frappe.db.get_value("Employee",finance_officiate[0].officiate,"user_id"):
			fa = 0
		#----------------------------IT Section Approver -----------------------------------------------------------------------------------------------------------------------------------------------------|
		it_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "itsa"))
		if frappe.session.user == frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "itsa"),"user_id"):
			ita = 0
		if it_officiate and frappe.session.user == frappe.db.get_value("Employee", it_officiate[0].officiate,"user_id"):
			ita = 0
		#----------------------------Internal Audit Approver -----------------------------------------------------------------------------------------------------------------------------------------------------|
		iaa_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "iaa"))
		if frappe.session.user == frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "iaa"),"user_id"):
			iaa = 0
		if iaa_officiate and frappe.session.user == frappe.db.get_value("Employee",iaa_officiate[0].officiate,"user_id"):
			iaa = 0
		#----------------------------Home Store Approver -----------------------------------------------------------------------------------------------------------------------------------------------------|
		hsa_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "hsa"))
		if frappe.session.user == frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "hsa"),"user_id"):
			hsa = 0
		if hsa_officiate and frappe.session.user == frappe.db.get_value("Employee", hsa_officiate[0].officiate,"user_id"):
			hsa = 0
		return fa, ita, iaa, hsa

	def get_receipients(self):
		receipients = []
		if self.fa:
			receipients.append(self.fa)
		if self.ita:
			receipients.append(self.ita)
		if self.iaa:
			receipients.append(self.iaa)
		if self.hsa:
			receipients.append(self.hsa)

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
		#----------------------------Finance Section -----------------------------------------------------------------------------------------------------------------------------------------------------------|
		finance_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "fsa"))
		if finance_officiate:
			self.fa = frappe.db.get_value("Employee",finance_officiate[0].officiate,"user_id")
		else:
			self.fa = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "fsa"),"user_id")
		
		#--------------------------- IT Section ----------------------------------------------------------------------------------------------------------------------------------------------------|
		ita_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "itsa"))
		if ita_officiate:
			self.ita = frappe.db.get_value("Employee",ita_officiate[0].officiate,"user_id")
		else:
			self.ita = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "itsa"),"user_id")
		
		#--------------------------- Internal Audit -----------------------------------------------------------------------------------------------------------------------------------------------------|
		iaa_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "iaa"))
		if iaa_officiate:
			self.iaa = frappe.db.get_value("Employee",iaa_officiate[0].officiate,"user_id")
		else:
			self.iaa = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "iaa"),"user_id")
		
		#--------------------------- Home Store -----------------------------------------------------------------------------------------------------------------------------------------------------|
		hsa_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "hsa"))
		if hsa_officiate:
			self.hsa = frappe.db.get_value("Employee",hsa_officiate[0].officiate,"user_id")
		else:
			self.hsa = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "hsa"),"user_id")

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
		(`tabEmployee Separation Clearance`.fa = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.ita = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.iaa = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.hsa = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)

	)""".format(user=user)