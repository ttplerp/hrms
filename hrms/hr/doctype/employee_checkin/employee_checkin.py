# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import now, cint, get_datetime, flt, nowdate, nowtime
from frappe.model.document import Document
from frappe import _
from datetime import datetime
from datetime import timedelta
from hrms.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift
import calendar
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

class EmployeeCheckin(Document):
	def validate(self):
		if self.type == "Office":
			self.check_travel_leave()
		self.validate_duplicate_log()
		self.mark_attendance()
		if (self.type == "Office" and self.log_type == "IN") or (self.type == "Office" and self.log_type == "OUT"):
			self.check_reason()

	def validate_duplicate_log(self):
		doc = frappe.db.exists('Employee Checkin', {
			'employee': self.employee,
			'date': self.date,
			'time': self.time,
			'log_type': self.log_type,
			'name': ['!=', self.name]})
		if doc:
			doc_link = frappe.get_desk_link('Employee Checkin', doc)
			frappe.throw(_('This employee already has a log with the same timestamp.{0}')
				.format("<Br>" + doc_link))

	def check_travel_leave(self):
		travel = frappe.db.sql("""
			select a.name from `tabTravel Request` a, `tabTravel Itinerary` b where b.parent=a.name and a.employee = '{0}'
			and a.docstatus = 1 and '{1}' between b.from_date and b.to_date
						 """.format(self.employee, self.date))
		if travel:
			frappe.throw("You cannot update since you are on tour.")
   
		leave = frappe.db.sql("""
			select name from `tabLeave Application` where half_day != 1 and employee = '{0}' and '{1}' between from_date and to_date and docstatus = 1
						""".format(self.employee, self.date))
		if leave:
			frappe.throw("You cannot update since you are on leave.")

	@frappe.whitelist()
	def current_date_time(self, shift=None):
		data = []
		# current_date = datetime.strptime(nowdate(), '%Y-%m-%d')
		office_in_start = frappe.db.get_value("Attendance Setting", "Office IN", "start_time")
		lunch_in_start = frappe.db.get_value("Attendance Setting", "Lunch IN", "start_time")
		lunch_in_end = frappe.db.get_value("Attendance Setting","Lunch IN", "end_time")
		lunch_out_start = frappe.db.get_value("Attendance Setting", "Lunch OUT", "start_time")
		lunch_out_end = frappe.db.get_value("Attendance Setting", "Lunch OUT", "end_time")
		office_out_start = frappe.db.get_value("Attendance Setting", "Office OUT", "start_time")
		# frappe.throw(str(data))
		if shift != None:
			shift_end_time = frappe.db.get_value("Shift Type", shift, "end_time")
			data.append({"office_in_start": office_in_start, "lunch_in_start": lunch_in_start, "lunch_in_end":lunch_in_end, "lunch_out_start":lunch_out_start, "lunch_out_end":lunch_out_end, "office_out_start": office_out_start, "shift_end_time": shift_end_time})
		else:
			data.append({"office_in_start": office_in_start, "lunch_in_start": lunch_in_start, "lunch_in_end":lunch_in_end, "lunch_out_start":lunch_out_start, "lunch_out_end":lunch_out_end, "office_out_start": office_out_start})
		return data

	def mark_attendance(self):
		branch = frappe.db.get_value("Employee",self.employee,"branch")
		day = calendar.day_name[self.date.weekday()]
		# frappe.throw(str(day))
		holiday_list = get_holiday_list_for_employee(self.employee)
		half_day = 0
		if holiday_list:
			half_working_days = frappe.db.sql("""
				select day from `tabHoliday List Days` where parent = '{0}'
        	""".format(holiday_list), as_dict=1)
			flag = 0
			for a in half_working_days:
				if day == a.day and flag == 0:
					half_day = 1
					flag = 1

		leave = frappe.db.sql("""
			select name from `tabLeave Application` where half_day = 1 and employee = '{0}' and '{1}' between from_date and to_date and docstatus = 1
		""".format(self.employee, self.date), as_dict=True)

		if leave and leave[0].name != None and leave[0].name != '':
			if self.log_type == "OUT" and self.type == "Office":
				date = datetime.strptime(str(self.date.date()), "%Y-%m-%d")
				attendance = frappe.db.sql("""
					select name from `tabAttendance` where shift = '{0}' and employee = '{1}'
					and attendance_date = '{2}' and docstatus = 1
				""".format(self.shift, self.employee, self.date))
				if attendance:
					frappe.msgprint("Your attendance is already marked for the day.")
				doc = frappe.new_doc("Attendance")
				doc.employee = self.employee
				doc.attendance_date = self.date
				doc.attendance_time = self.datetime
				doc.time_difference = self.time_difference
				doc.shift = self.shift
				if half_day == 0:
					doc.status = "Half Day"
				elif half_day == 1:
					doc.status = "Present"
				doc.save(ignore_permissions=True)
				doc.submit()
		else:
			if self.log_type == "OUT" and self.type == "Office":
				date = datetime.strptime(str(self.date.date()), "%Y-%m-%d")
				attendance = frappe.db.sql("""
					select name from `tabAttendance` where shift = '{0}' and status != "Half Day" and employee = '{1}'
					and attendance_date = '{2}' and docstatus = 1
				""".format(self.shift, self.employee, self.date))
				if attendance:
					frappe.msgprint("Your attendance is already marked for the day.")
				att = frappe.db.sql("""
					select name from `tabAttendance` where shift = '{0}' and status = "Half Day" and employee = '{1}'
					and attendance_date = '{2}' and docstatus = 1
				""".format(self.shift, self.employee, self.date), as_dict = True)
				
				#change
				if half_day != 1:
					doc = frappe.get_doc("Attendance",att[0].name)
					in_time = frappe.db.get_value("Attendance",att[0].name,"in_time")
					if self.reason:
						doc.early_exit = "1"
						doc.reason_for_early_exit =str(self.reason)
					#calcuation for total working hours
					if self.time:						 
						out_time = datetime.strptime(self.date.strftime("%Y-%m-%d") + " " + self.time, "%Y-%m-%d %H:%M:%S.%f")						 
						doc.out_time = out_time.isoformat() 

						if doc.in_time:							 
							time_difference = out_time - doc.in_time							 
							total_seconds = time_difference.total_seconds()							 
							total_hours = int(total_seconds // 3600)
							remaining_minutes = int((total_seconds % 3600) // 60)
							# Format the hours and minutes as "H:MM"
							doc.total_working_hours = f"{total_hours}:{remaining_minutes:02d}"
							 
						else:
							pass
							# frappe.throw("In-time is not defined.")
					else:
						frappe.throw("Time is not defined.")
					
					doc.status = "Present"
					doc.save(ignore_permissions=True)

			elif self.log_type == "IN" and self.type == "Office":
				date = datetime.strptime(str(self.date.date()), "%Y-%m-%d")
				attendance = frappe.db.sql("""
					select name from `tabAttendance` where shift = '{0}' and employee = '{1}'
					and attendance_date = '{2}' and docstatus = 1 and status != 'Half Day'
				""".format(self.shift, self.employee, self.date))
				if attendance:
					frappe.throw("Your attendance is already marked for the day.")
				att_request = frappe.db.sql("""
					select name from `tabAttendance Request` where employee = '{0}'
					and '{1}' between from_date and to_date and half_day = 1
			    """.format(self.employee, self.date), as_dict=1)

				if not att_request:
					doc = frappe.new_doc("Attendance")
					doc.employee = self.employee
					doc.attendance_date = self.date					
					doc.attendance_time = self.time
					# doc.time_difference = self.time_difference
					doc.shift = self.shift

					if self.time:						 
   						 doc.in_time = datetime.strptime(self.date.strftime("%Y-%m-%d") + " " + self.time, "%Y-%m-%d %H:%M:%S.%f")    					 
   						 doc.in_time = doc.in_time.isoformat()
						 	
					if self.reason:
						doc.late_entry = 1
						doc.reason_for_late_entry = self.reason
					if half_day == 0:
						doc.status = "Half Day"
					elif half_day == 1:
						doc.status = "Present"

					doc.total_working_hours=""
					doc.save(ignore_permissions=True)
					doc.submit()
					

				

	def check_reason(self):
		if self.reason:
			pass
			# self.send_email()

	def send_email(self):
		"""Send Email to Supervisor and HR Manager if late office in or early exit"""
		recipients = []
		subject = ""

		supervisor = frappe.db.get_value("Employee",frappe.db.get_value("Employee",self.employee,"reports_to"),"user_id")
		if supervisor:
			recipients.append(supervisor)

		if self.log_type == "IN" and self.type == "Office":
			subject = "Reason for late Office IN"
		elif self.log_type == "OUT" and self.type == "Office":
			subject = "Reason for early Office OUT"
		# time = datetime.strptime(str(self.time),"%H:%i %p")
		time = frappe.format_value(self.time,{'fieldtype':'Time'})
		message = """
					<ul>
						<li><b>Employee:</b>{}</li>
						<li><b>Employee Name:</b>{}</li>
						<li><b>Time:</b>{}</li>
						<li><b>Reason:</b>{}</li>
					</ul>
				  """.format(self.employee, frappe.db.get_value("Employee",self.employee,"employee_name"), time, self.reason)
		try:
			frappe.sendmail(recipients=recipients,
				subject=_(subject),
				message=message,
				header=['Employee Checkin Notification', 'red'],
			)
		except frappe.OutgoingEmailError:
			pass


@frappe.whitelist()
def add_log_based_on_employee_field(employee_field_value, timestamp, device_id=None, log_type=None, skip_auto_attendance=0, employee_fieldname='attendance_device_id'):
	"""Finds the relevant Employee using the employee field value and creates a Employee Checkin.

	:param employee_field_value: The value to look for in employee field.
	:param timestamp: The timestamp of the Log. Currently expected in the following format as string: '2019-05-08 10:48:08.000000'
	:param device_id: (optional)Location / Device ID. A short string is expected.
	:param log_type: (optional)Direction of the Punch if available (IN/OUT).
	:param skip_auto_attendance: (optional)Skip auto attendance field will be set for this log(0/1).
	:param employee_fieldname: (Default: attendance_device_id)Name of the field in Employee DocType based on which employee lookup will happen.
	"""

	if not employee_field_value or not timestamp:
		frappe.throw(_("'employee_field_value' and 'timestamp' are required."))

	employee = frappe.db.get_values("Employee", {employee_fieldname: employee_field_value}, ["name", "employee_name", employee_fieldname], as_dict=True)
	if employee:
		employee = employee[0]
	else:
		frappe.throw(_("No Employee found for the given employee field value. '{}': {}").format(employee_fieldname,employee_field_value))

	doc = frappe.new_doc("Employee Checkin")
	doc.employee = employee.name
	doc.employee_name = employee.employee_name
	doc.time = timestamp
	doc.device_id = device_id
	doc.log_type = log_type
	if cint(skip_auto_attendance) == 1: doc.skip_auto_attendance = '1'
	doc.insert()

	return doc


def mark_attendance_and_link_log(logs, attendance_status, attendance_date, working_hours=None, late_entry=False, early_exit=False, shift=None):
	"""Creates an attendance and links the attendance to the Employee Checkin.
	Note: If attendance is already present for the given date, the logs are marked as skipped and no exception is thrown.

	:param logs: The List of 'Employee Checkin'.
	:param attendance_status: Attendance status to be marked. One of: (Present, Absent, Half Day, Skip). Note: 'On Leave' is not supported by this function.
	:param attendance_date: Date of the attendance to be created.
	:param working_hours: (optional)Number of working hours for the given date.
	"""
	log_names = [x.name for x in logs]
	employee = logs[0].employee
	if attendance_status == 'Skip':
		frappe.db.sql("""update `tabEmployee Checkin`
			set skip_auto_attendance = %s
			where name in %s""", ('1', log_names))
		return None
	elif attendance_status in ('Present', 'Absent', 'Half Day'):
		employee_doc = frappe.get_doc('Employee', employee)
		if not frappe.db.exists('Attendance', {'employee':employee, 'attendance_date':attendance_date, 'docstatus':('!=', '2')}):
			doc_dict = {
				'doctype': 'Attendance',
				'employee': employee,
				'attendance_date': attendance_date,
				'in_time': in_time,
				'out_time': out_time,
				'status': attendance_status,
				'working_hours': working_hours,
				'company': employee_doc.company,
				'shift': shift,
				'late_entry': late_entry,
				'early_exit': early_exit
			}
			attendance = frappe.get_doc(doc_dict).insert()
			attendance.submit()
			frappe.db.sql("""update `tabEmployee Checkin`
				set attendance = %s
				where name in %s""", (attendance.name, log_names))
			return attendance
		else:
			frappe.db.sql("""update `tabEmployee Checkin`
				set skip_auto_attendance = %s
				where name in %s""", ('1', log_names))
			return None
	else:
		frappe.throw(_('{} is an invalid Attendance Status.').format(attendance_status))


def calculate_working_hours(logs, check_in_out_type, working_hours_calc_type):
	"""Given a set of logs in chronological order calculates the total working hours based on the parameters.
	Zero is returned for all invalid cases.
	
	:param logs: The List of 'Employee Checkin'.
	:param check_in_out_type: One of: 'Alternating entries as IN and OUT during the same shift', 'Strictly based on Log Type in Employee Checkin'
	:param working_hours_calc_type: One of: 'First Check-in and Last Check-out', 'Every Valid Check-in and Check-out'
	"""
	total_hours = 0
	in_time = out_time = None
	if check_in_out_type == 'Alternating entries as IN and OUT during the same shift':
		in_time = logs[0].time
		if len(logs) >= 2:
			out_time = logs[-1].time
		if working_hours_calc_type == 'First Check-in and Last Check-out':
			# assumption in this case: First log always taken as IN, Last log always taken as OUT
			total_hours = time_diff_in_hours(in_time, logs[-1].time)
		elif working_hours_calc_type == 'Every Valid Check-in and Check-out':
			logs = logs[:]
			while len(logs) >= 2:
				total_hours += time_diff_in_hours(logs[0].time, logs[1].time)
				del logs[:2]

	elif check_in_out_type == 'Strictly based on Log Type in Employee Checkin':
		if working_hours_calc_type == 'First Check-in and Last Check-out':
			first_in_log_index = find_index_in_dict(logs, 'log_type', 'IN')
			first_in_log = logs[first_in_log_index] if first_in_log_index or first_in_log_index == 0 else None
			last_out_log_index = find_index_in_dict(reversed(logs), 'log_type', 'OUT')
			last_out_log = logs[len(logs)-1-last_out_log_index] if last_out_log_index or last_out_log_index == 0 else None
			if first_in_log and last_out_log:
				in_time, out_time = first_in_log.time, last_out_log.time
				total_hours = time_diff_in_hours(in_time, out_time)
		elif working_hours_calc_type == 'Every Valid Check-in and Check-out':
			in_log = out_log = None
			for log in logs:
				if in_log and out_log:
					if not in_time:
						in_time = in_log.time
					out_time = out_log.time
					total_hours += time_diff_in_hours(in_log.time, out_log.time)
					in_log = out_log = None
				if not in_log:
					in_log = log if log.log_type == 'IN'  else None
				elif not out_log:
					out_log = log if log.log_type == 'OUT'  else None
			if in_log and out_log:
				out_time = out_log.time
				total_hours += time_diff_in_hours(in_log.time, out_log.time)
	return total_hours, in_time, out_time

def time_diff_in_hours(start, end):
	return round((end-start).total_seconds() / 3600, 1)

def find_index_in_dict(dict_list, key, value):
	return next((index for (index, d) in enumerate(dict_list) if d[key] == value), None)

# restrick user from accessing this doctype 
def get_permission_query_conditions(user):   
	if not user: user = frappe.session.user     
	user_roles = frappe.get_roles(user)
	if user == "Administrator":      
		return
	if "System Manager" in user_roles: 
		return
	if "HR Manager" in user_roles: 
		return
	if "HR User" in user_roles: 
		return

	return """(
		`tabEmployee Checkin`.owner = '{user}'
		)""".format(user=user)


