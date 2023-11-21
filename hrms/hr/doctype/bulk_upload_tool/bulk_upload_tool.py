# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import msgprint
from frappe.utils import cstr, add_days, date_diff, cint, flt, getdate, nowdate
from frappe import _
from frappe.utils.csvutils import UnicodeWriter
from frappe.model.document import Document
from datetime import datetime
from calendar import monthrange
import csv
import os
from functools import reduce
from frappe import _
from frappe.utils.xlsxutils import (
	read_xls_file_from_attached_file,
	read_xlsx_file_from_attached_file,
)
class BulkUploadTool(Document):
	pass

	@frappe.whitelist()
	def upload_data(self):
		if self.upload_type == "Overtime":
			doctype = "Muster Roll Overtime Entry"
		else:
			doctype = "Muster Roll Attendance"
		if not frappe.has_permission(doctype, "create"):
			raise frappe.PermissionError

		from frappe.utils.csvutils import read_csv_content_from_attached_file
		from frappe.modules import scrub
		if frappe.safe_encode(self.import_file).lower().endswith("csv".encode("utf-8")):
			from frappe.utils.csvutils import read_csv_content
			file_name = frappe.get_doc("File", {"file_url": self.import_file})
			fcontent = file_name.get_content()
			rows = read_csv_content(fcontent)

		elif frappe.safe_encode(self.import_file).lower().endswith("xlsx".encode("utf-8")):			
			try:
				file_name = frappe.get_doc("File", {"file_url": self.import_file})
				fcontent = file_name.get_content()
				rows = read_xlsx_file_from_attached_file(fcontent = fcontent, filepath=self.import_file)
			except Exception:
				frappe.throw(
					_("Unable to open attached file. Did you export it as excel?"), title=_("Invalid Excel Format")
				)
		if not rows:
			msg = [_("Please select a csv/excel file")]
			return {"messages": msg, "error": msg}
		ret = []
		error = False
		total_count = len(rows)-1
		count = successful = failed = 0
		refresh_interval = 1
		
		from frappe.utils.csvutils import check_record, import_doc

		for i, row in enumerate(rows[1:]):
			if not row: continue
			count += 1
			try:
				row_idx = i + 7
				year = row[6]
				for j in range(9, len(row)+1):
					month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(row[7])
					month = cint(month) + 1
					month = str(month) if cint(month) > 9 else str("0" + str(month))
					day   = cint(j)-8 if cint(j) > 9 else "0" + str(cint(j)-8)
					date_str = f"{year}-{month}-{day}"

					if self.upload_type == "Overtime":
						# frappe.throw(str(row))
						# frappe.throw(str(row[4])+' <--> '+str(row[9]))
						old = frappe.db.get_value("Muster Roll Overtime Entry", {"mr_employee":str(row[4]).strip('\''), "date": date_str, "docstatus": 1}, ["docstatus","name","number_of_hours"], as_dict=1)
						# frappe.throw(str(old))
						
						if old:
							doc = frappe.get_doc("Muster Roll Overtime Entry", old.name)
							doc.db_set('number_of_hours', flt(row[j-1]) if row[j-1] else doc.number_of_hours)
						if not old and flt(row[j-1]) > 0:
							doc = frappe.new_doc("Muster Roll Overtime Entry")
							doc.branch          	= row[0]
							doc.cost_center     	= row[1]
							doc.muster_roll_type 	= row[2]
							doc.mr_employee     	= str(row[4]).strip('\'')
							doc.mr_employee_name	= str(row[5]).strip('\'')
							doc.date            	= str(row[6]) + '-' + str(month) + '-' + str(day)
							doc.number_of_hours 	= flt(row[j -1])
							doc.reference			= self.name
																				
							if not getdate(doc.date) > getdate(nowdate()):
								doc.submit()
					else:
						# frappe.throw(str(row[2]).strip('\''))
						status = ''
						if str(row[j -1]) in ("P","p","1"):
							status = 'Present'
						elif str(row[j -1]) in ("A","a","0"):
							status = 'Absent'
						elif str(row[j -1]) in ("H","h","0.5"):
							status = 'Half Day'
						else:
							status = ''
						

						old = frappe.db.get_value("Muster Roll Attendance", {"mr_employee": str(row[4]).strip('\''), "date": date_str, "docstatus": 1}, ["status","name"], as_dict=1)
						if old:
							doc = frappe.get_doc("Muster Roll Attendance", old.name)
							doc.db_set('status', status if status in ('Present','Absent','Half Day') else doc.status)
							doc.db_set('branch', row[0])
							doc.db_set('cost_center', row[1])
							# doc.db_set('unit', row[2])
						# frappe.throw(str(row[2]).strip('\''))
						if not old and status in ('Present','Absent','Half Day'):
							doc = frappe.new_doc("Muster Roll Attendance")
							doc.status = status
							doc.branch = row[0]
							doc.cost_center = row[1]
							doc.muster_roll_type = row[2]
							doc.mr_employee = str(row[4]).strip('\'')
							doc.mr_employee_name = str(row[5]).strip('\'')
							doc.date = str(row[6]) + '-' + str(month) + '-' + str(day)
							doc.reference = self.name
							if not datetime.strptime(str(doc.date), "%Y-%m-%d") > datetime.strptime(str(nowdate()),"%Y-%m-%d"):
								doc.submit()
					successful += 1
			except Exception as e:
				failed += 1
				error = True
				ret.append('Error for row (#%d) %s : %s' % (row_idx,
					len(row)>1 and row[4] or "", cstr(e)))
				frappe.errprint(frappe.get_traceback())
		if error:
			frappe.db.rollback()
		else:
			frappe.db.commit()

		show_progress = 0
		if count <= refresh_interval:
			show_progress = 1
		elif refresh_interval > total_count:
			show_progress = 1
		elif count%refresh_interval == 0:
			show_progress = 1
		elif count > total_count-refresh_interval:
			show_progress = 1
		
		if show_progress:
			description = " Processing OT Of {}({}): ".format(frappe.bold(str(row[3]).strip('\'')),frappe.bold(row[2])) + "["+str(count)+"/"+str(total_count)+"]"
			# frappe.throw(str(description))
			frappe.publish_progress(count*100/total_count,
				title = _("Posting Overtime Entry..."),
				description = description)
			pass
		return {"messages": ret, "error": error}

@frappe.whitelist()
def download_template(file_type, branch, month, muster_roll_type, muster_roll_group, fiscal_year, upload_type):
	data = frappe._dict(frappe.local.form_dict)
	writer = get_template(branch, muster_roll_type, muster_roll_group, month, fiscal_year)
	for d in get_mr_data(branch, muster_roll_type, muster_roll_group, month, fiscal_year):
		row = []
		row.append(d.branch)
		row.append(d.cost_center)
		row.append(d.muster_roll_type)
		row.append(d.muster_roll_group)
		row.append(d.name)
		row.append(d.person_name)
		row.append(d.fiscal_year)
		row.append(d.month)
		writer.writerow(row)
	if upload_type == "Overtime":
		doctype = "Muster Roll Overtime Entry"
	else:
		doctype = "Muster Roll Attendance"
	if file_type == "CSV":
		# download csv file
		frappe.response["result"] = cstr(writer.getvalue())
		frappe.response["type"] = "csv"
		frappe.response["doctype"] = doctype
	else:
		build_response_as_excel(writer,doctype)

def build_response_as_excel(writer, doctype):
	filename = frappe.generate_hash("", 10)
	with open(filename, "wb") as f:
		f.write(cstr(writer.getvalue()).encode("utf-8"))
	f = open(filename)
	reader = csv.reader(f)

	from frappe.utils.xlsxutils import make_xlsx

	xlsx_file = make_xlsx(reader, doctype)

	f.close()
	os.remove(filename)

	# write out response as a xlsx type
	frappe.response["filename"] = str(doctype) + ".xlsx"
	frappe.response["filecontent"] = xlsx_file.getvalue()
	frappe.response["type"] = "binary"
def get_mr_data(branch, muster_roll_type, muster_roll_group, month, fiscal_year):
	mr_condition = ""
	if muster_roll_type:
		mr_condition = " and muster_roll_type = '{}'".format(muster_roll_type)
	if muster_roll_group:
		mr_condition = " and muster_roll_group = '{}'".format(muster_roll_group)
	if branch:
		mr_condition = " and branch = '{}'".format(branch)
	else:
		mr_condition = ""
	return frappe.db.sql('''select branch, cost_center, muster_roll_type, muster_roll_group, unit, name, person_name,
						 "{fiscal_year}" as fiscal_year, "{month}" as month
						from `tabMuster Roll Employee`
						where status ="Active"
						{mr_condition}
						'''.format(mr_condition = mr_condition, month=month, fiscal_year=fiscal_year), as_dict=True)
	
def get_template(branch, muster_roll_type, muster_roll_group, month, fiscal_year):
	if not frappe.has_permission("Muster Roll Overtime Entry", "create"):
		raise frappe.PermissionError
	month_in_number = frappe._dict({
									"Jan":1,
									"Feb":2,
									"Mar":3,
									"Apr":4,
									"May":5,
									"Jun":6,
									"Jul":7,
									"Aug":8,
									"Sep":9,
									"Oct":10,
									"Nov":11,
									"Dec":12,
								})
	
	fields = ["Branch", "Cost Center", "Muster Roll Type", "Muster Roll Group", "Employee ID", "Employee Name", "Year", "Month"]
	total_days = monthrange(cint(fiscal_year), month_in_number[str(month)])[1]
	for day in range(cint(total_days)):
		fields.append(str(month)+'_'+str(day + 1))	
	writer = UnicodeWriter()
	writer.writerow(fields)

	return writer