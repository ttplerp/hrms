# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class OTUpdateTools(Document):
	def validate(self):
		self.calculate_total_amount()
		self.validate_duplicate()
		if self.workflow_state!="Draft":
			self.send_notification()

	def on_submit(self):
		pass
		#self.post_overtime_entries()
	
	def on_cancel(self):
		frappe.db.sql("Update `tabOT Update Tools` set workflow_state='Cancelled' where name='{}'".format(self.name))
		frappe.db.commit()
	
	def validate_duplicate(self):
		for a in self.get("ot_details"):
			duplicate = 0
			doc = frappe.get_doc("Employee", a.employee)
			if doc.status != "Active":
				frappe.throw("Employee <b>{} {}</b> status is {}. OT is allowed only for <b>Active</b> employee".format(a.employee, a.employee_name, doc.status))
			for b in self.get("ot_details"):
				if a.employee == b.employee:
					duplicate += 1
			if duplicate > 1:
				frappe.throw("Duplicate entry for Employee <b>{}, {}</b>. Please check".format(a.employee, a.employee_name))

			if self.name:
				for c in frappe.db.sql("""
								select t.name
								from `tabOT Update Tools` t
								inner join `tabOT tools items` i on t.name=i.parent
								where i.employee ='{}'
								and t.posting_date='{}'
								and t.docstatus!=2
								and t.name != '{}'
							""".format(a.employee, self.posting_date, self.name), as_dict=True):
					frappe.throw("Employee <b>{}, {}</b> OT for date <b>{}</b> is already recorded with <b>{} </b>".format(a.employee, a.employee_name, self.posting_date,c.name))
		

		#Check for Temporary Staffs
		for a in self.get("temporary_staff_details"):
			duplicate = 0
			doc = frappe.get_doc("TES_Temporary Staffs", a.name_code)
			for b in self.get("temporary_staff_details"):
				if a.name_code == b.name_code:
					duplicate += 1
			
			if duplicate > 1:
				frappe.throw("Duplicate entry for Temporary Employee <b>{}, {}</b>. Please check".format(a.name_code, a.full_name)) 

			if self.name:
				for c in frappe.db.sql("""
								select t.name
								from `tabOT Update Tools` t
								inner join `tabTemporary staff items` i on t.name=i.parent
								where i.name_code ='{}'
								and t.posting_date='{}'
								and t.docstatus!=2
								and t.name != '{}'
							""".format(a.name_code, self.posting_date, self.name), as_dict=True):
					frappe.throw("Temporary Employee <b>{}, {}</b> OT for date <b>{}</b> is already recorded with <b>{} </b>".format(a.name_code, a.full_name, self.posting_date,c.name))
 
	def calculate_total_amount(self):
		total_amount, temp_total_amount = 0.00, 0.00
		for row in self.ot_details:
			if not row.ot_amount:
				frappe.throw("OT amount cannot be zero for {}, {}".format(row.employee, row.employee_name))
			if not row.approved_ot_hrs:
				frappe.throw("Please enter approved OT hours {}, {}".format(row.employee, row.employee_name)) 

			if row.overtime_type == "Sunday Overtime (Half Day)":
				if row.ot_rate_half_day < 1:
					frappe.throw("Rate for {} cannot be {} for {}, {}".format(row.overtime_type, row.ot_rate_half_day, row.employee, row.employee_name))
				row.ot_amount = flt(row.ot_rate_half_day,2)
			elif row.overtime_type == "Sunday Overtime (Full Day)":
				if row.ot_rate_full_day < 1:
					frappe.throw("Rate for {} cannot be {} for {}, {}".format(row.overtime_type, row.ot_rate_full_day, row.employee, row.employee_name))
				row.ot_amount=flt(row.ot_rate_full_day,2)
			else:
				if row.ot_rate < 1:
					frappe.throw("Overtime Rate for {}, {} cannot be less than 1".format(row.employee, row.employee_name))
				row.ot_amount = flt(row.ot_rate * row.approved_ot_hrs, 2)
			total_amount += flt(row.ot_amount,2)
		
		for row in self.temporary_staff_details:
			if not row.temp_ot_amount:
				frappe.throw("OT amount cannot be zero for temporary staff {}, {}".format(row.name_code, row.full_name))
			if not row.approved_ot_hours:
				frappe.throw("Please enter approved OT hours for Temporary staff {}, {}".format(row.name_code, row.full_name)) 

			if row.ot_type == "Sunday Overtime (Half Day)":
				if row.half_day < 1:
					frappe.throw("Rate for {} cannot be {} for {}, {}".format(row.ot_type, row.half_day, row.name_code, row.full_name))
				row.temp_ot_amount = flt(row.half_day,2)
			elif row.ot_type == "Sunday Overtime (Full Day)":
				if row.full_day < 1:
					frappe.throw("Rate for {} cannot be {} for {}, {}".format(row.ot_type, row.full_day, row.name_code, row.full_name))
				row.temp_ot_amount=flt(row.full_day,2)
			else:
				if row.rates < 1:
					frappe.throw("Overtime Rate for temporary employee {}, {} cannot be less than 1".format(row.name_code, row.full_name))
				row.temp_ot_amount = flt(row.rates * row.approved_ot_hours, 2)
			temp_total_amount += flt(row.temp_ot_amount,2)
		self.total_amount = flt(total_amount,2) + flt(temp_total_amount,2)
	
	def get_args(self):
		parent_doc = frappe.get_doc(self.doctype, self.name)
		args = parent_doc.as_dict()
		return args
	
	def send_notification(self):
		args = self.get_args()
		recipient=[]
		recipient.append(self.approver)
		if self.workflow_state == "Waiting Supervisor Approval":
			'''
			for user in frappe.get_all('Has Role', filters={'role': role_name}, fields=['parent']):
				recipient.append(user['parent'])
			'''
			template = "OT Update Tools"
			email_template = frappe.get_doc("Email Template", template)
			message = frappe.render_template(email_template.response, args)
			recipients = recipient
			subject = email_template.subject
			frappe.sendmail(recipients=recipients,subject=subject, message=message, attachments=None)
		
	@frappe.whitelist()
	def post_overtime_entries(self):
		for d in self.get("ot_details"):
			doc = frappe.new_doc("Overtime Application")
			doc.employee = d.employee
			doc.company = self.company
			doc.posting_date = self.posting_date
			doc.purpose = self.memo
			doc.ot_update_tool = self.name
			if d.overtime_type == "Overtime (Normal Rate)":
				rate = d.ot_rate
			elif d.overtime_type == "Sunday Overtime (Half Day)":
				rate = d.ot_rate_half_day
			else:
				rate = d.ot_rate_full_day
			doc.append("items",{
				"overtime_type":d.overtime_type,
				"from_date": str(self.posting_date) + " " + str(d.from_date),
				"to_date": str(self.posting_date) + " " + str(d.to_date),
				"number_of_hours":d.number_of_hours,
				"ot_rate": flt(rate,2),
				"approved_ot_hrs":d.approved_ot_hrs,
				"ot_amount":flt(d.ot_amount,2),
				"remarks": d.remarks
			})
			doc.save()
			doc.submit()
		
		frappe.db.sql("Update `tabOT Update Tools` set workflow_state='Recorded' where name='{}'".format(self.name))
		frappe.db.commit()

@frappe.whitelist()
def get_rate(employee, overtime_type):
	return frappe.db.get_value("Employee", employee, ["overtime_normal_rate","sunday_overtime_half_day","sunday_overtime_full_day"])

@frappe.whitelist()
def get_temp_overtime_rate(staff):
	return frappe.db.get_value("TES_Temporary Staffs", staff, ["normal_ot_rate","sunday_half_day","sunday_full_day"])