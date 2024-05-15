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

	def on_submit(self):
		self.post_overtime_entries()
	
	def validate_duplicate(self):
		for a in self.get("ot_details"):
			duplicate = 0
			doc = frappe.get_doc("Employee", a.employee)
			if doc.status != "Active":
				frappe.throw("Employee <b>{} {}</b> status is {}. OT is allowed only for <b>Active</b> employee".format(a.employee, a.employee_name, doc.status))
			for b in self.get("ot_details"):
				if a.employee == b.employee:
					duplicate += 1

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
			
			if duplicate > 1:
				frappe.throw("Duplicate entry for Employee <b>{}, {}</b>. Please check".format(a.employee, a.employee_name)) 

	def calculate_total_amount(self):
		total_amount = 0.00
		for row in self.ot_details:
			if not row.ot_amount:
				frappe.throw("OT amount cannot be zero")
			if not row.approved_ot_hrs:
				frappe.throw("Please enter approved OT hours") 

			if row.overtime_type == "Sunday Overtime (Half Day)":
				if row.ot_rate_half_day < 1:
					frappe.throw("Rate for {} cannot be {}".format(row.overtime_type, row.ot_rate_half_day))
				row.ot_amount = flt(row.ot_rate_half_day,2)
			elif row.overtime_type == "Sunday Overtime (Full Day)":
				if row.ot_rate_full_day < 1:
					frappe.throw("Rate for {} cannot be {}".format(row.overtime_type, row.ot_rate_full_day))
				row.ot_amount=flt(row.ot_rate_full_day,2)
			else:
				if row.ot_rate < 1:
					frappe.throw("Overtime Rate cannot be {}".format(row.ot_rate))
				row.ot_amount = flt(row.ot_rate * row.approved_ot_hrs, 2)
			total_amount += flt(row.ot_amount,2)
		self.total_amount = flt(total_amount,2)

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

@frappe.whitelist()
def get_rate(employee, overtime_type):
	return frappe.db.get_value("Employee", employee, ["overtime_normal_rate","sunday_overtime_half_day","sunday_overtime_full_day"])
