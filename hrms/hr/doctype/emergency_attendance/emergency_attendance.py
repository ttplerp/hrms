# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime,timedelta
from frappe import _
from frappe.utils import (
	add_days,
	cint,
	cstr,
	date_diff,
	flt,
	formatdate,
	nowtime,
	getdate,
	nowdate
)
from hrms.hr.utils import (
	get_holiday_dates_for_employee
)
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states

class EmergencyAttendance(Document):
	def validate(self):
		validate_workflow_states(self)
		self.validate_shift_leave_tour()
		self.set_time()
		if self.workflow_state != "Approved":
			notify_workflow_states(self)
	def on_submit(self):
		self.update_total_working_hr()
		self.check_working_hr()

	def set_time(self):
		if not self.check_in:
			self.check_in = frappe.utils.now_datetime()
		if self.workflow_state=="Waiting Approval":
			self.check_out = frappe.utils.now_datetime()
		if self.check_out:
			self.update_total_working_hr()
	def check_working_hr(self):
		if not self.total_working_hr:
			frappe.throw("Total Working hr is required")

	def update_total_working_hr(self):
		if self.check_in and self.check_out:
			self.total_working_hr = self.check_out - self.check_in


	def validate_shift_leave_tour(self):
		if not self.employee:
			frappe.throw("Employee is Required")
		if not self.check_in:
			self.check_in = str(nowdate())+" "+str(nowtime()).split(".")[0]
		holiday_dates = get_holiday_dates_for_employee(self.employee, self.posting_date, self.posting_date)
		leave = frappe.db.sql("""
			SELECT name
			FROM `tabLeave Application`
			WHERE docstatus != 2
			AND from_date <= %s
			AND to_date >= %s
			AND employee = %s
			""", (self.posting_date, self.posting_date, self.employee), as_dict=True)
		posting_date = datetime.strptime(str(self.posting_date), "%Y-%m-%d")
		month_number = posting_date.month
		months_name = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
		month = months_name[month_number - 1]  # Adjusting index since month_number is 1-based

		shift = frappe.db.sql("""
			select ash.shift_type , sd.*
			from `tabAssign Shift` ash
			INNER JOIN `tabShift Details` sd  
			ON ash.name = sd.parent
			where ash.month ='{0}'
			and sd.employee='{1}'
			and ash.docstatus = 1
		""".format(month,self.employee), as_dict=True)
		if not holiday_dates:
			if not leave:
				if shift:
					for d in shift:
						if any(getattr(d, f'{i}') == 1 for i in range(1, 31)):
							start_time = datetime.strptime(str(nowdate())+" "+str(d.start_time), '%Y-%m-%d %H:%M:%S')
							end_time = datetime.strptime(str(nowdate())+" "+str(d.end_time), '%Y-%m-%d %H:%M:%S')
							# Assuming self.check_in is also a string in the format 'HH:MM:SS'
							check_in_time = datetime.strptime(self.check_in, '%Y-%m-%d %H:%M:%S')
							
							if start_time < check_in_time <= end_time:
								frappe.throw("Cannot apply emergency attendance while your shift is not over")
				if not shift:
					office_in = frappe.db.get_value("Shift Type","General Shift","start_time")
					office_out =frappe.db.get_value("Shift Type","General Shift","end_time")
					start_time = datetime.strptime(str(nowdate())+" "+str(office_in), '%Y-%m-%d %H:%M:%S')
					end_time = datetime.strptime(str(nowdate())+" "+str(office_out), '%Y-%m-%d %H:%M:%S')
					check_in_time = datetime.strptime(self.check_in, '%Y-%m-%d %H:%M:%S')
				
					if start_time < check_in_time <= end_time:
						frappe.throw("Cannot apply emergency attendance while your shift is not over")
		
	
