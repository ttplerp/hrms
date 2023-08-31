# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import msgprint
from frappe.utils import cstr, add_days, date_diff, cint, flt, getdate, nowdate
from frappe import _
from frappe.utils.csvutils import UnicodeWriter
from frappe.model.document import Document
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
				rows = read_xlsx_file_from_attached_file(fcontent=fcontent, filepath=self.import_file)
			except Exception:
				frappe.throw(
					_("Unable to open attached file. Did you export it as excel?"), title=_("Invalid Excel Format")
				)
		if not rows:
			msg = [_("Please select a csv/excel file")]
			return {"messages": msg, "error": msg}
		ret = []
		error = False
		total_count = len(rows) - 1
		count = successful = failed = 0
		refresh_interval = 1
		from frappe.utils.csvutils import check_record, import_doc

		for i, row in enumerate(rows[1:]):
			if not row:
				continue
			count += 1
			try:
				row_idx = i + 6
				year = row[5]
				month = row[6]

				for day_idx, day_value in enumerate(row[7:], start=1):
					if not str(day_value).strip():
						continue

					day = str(day_idx) if day_idx > 9 else "0" + str(day_idx)
					month_number = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(row[6]) + 1
					month_str = str(month_number).zfill(2)
					year = row[5]
					date_str = f"{year}-{month_str}-{day}" 

					if self.upload_type == "Overtime":
						old = frappe.db.get_value("Muster Roll Overtime Entry", {"mr_employee": str(row[3]).strip('\''), "date": date_str, "docstatus": 1}, ["docstatus", "name", "number_of_hours"], as_dict=1)
						if old:
							doc = frappe.get_doc("Muster Roll Overtime Entry", old.name)
							doc.db_set('number_of_hours', flt(day_value))
						if not old and flt(day_value) > 0:
							doc = frappe.new_doc("Muster Roll Overtime Entry")
							doc.branch = row[0]
							doc.cost_center = row[1]
							doc.unit = row[2]
							doc.mr_employee = str(row[3]).strip('\'')
							doc.mr_employee_name = str(row[4]).strip('\'')
							doc.date = date_str
							doc.number_of_hours = flt(day_value)
							doc.reference = self.name

							if not getdate(doc.date) > getdate(nowdate()):
								doc.submit()
					else:
						status = ''
						if str(day_value) in ("P", "p", "1"):
							status = 'Present'
						elif str(day_value) in ("A", "a", "0"):
							status = 'Absent'
						else:
							status = ''

						old = frappe.db.get_value("Muster Roll Attendance", {"mr_employee": str(row[3]).strip('\''), "date": date_str, "docstatus": 1}, ["status", "name"], as_dict=1)
						if old:
							doc = frappe.get_doc("Muster Roll Attendance", old.name)
							doc.db_set('status', status if status in ('Present', 'Absent') else doc.status)
							doc.db_set('branch', row[0])
							doc.db_set('cost_center', row[1])
							doc.db_set('unit', row[2])
						if not old and status in ('Present', 'Absent'):
							doc = frappe.new_doc("Muster Roll Attendance")
							doc.status = status
							doc.branch = row[0]
							doc.cost_center = row[1]
							doc.unit = row[2]
							doc.mr_employee = str(row[3]).strip('\'')
							doc.mr_employee_name = str(row[4]).strip('\'')
							doc.date = date_str
							doc.reference = self.name

							# if not getdate(doc.date) > getdate(nowdate()):
							doc.submit()
					successful += 1

			except Exception as e:
				failed += 1
				error = True
				ret.append('Error for row (#%d) %s : %s' % (row_idx, len(row) > 1 and row[5] or "", cstr(e)))
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
		elif count % refresh_interval == 0:
			show_progress = 1
		elif count > total_count - refresh_interval:
			show_progress = 1

		if show_progress:
			description = " Processing OT Of {}({}): ".format(frappe.bold(str(row[4]).strip('\'')), frappe.bold(row[3])) + "[" + str(count) + "/" + str(total_count) + "]"
			frappe.publish_progress(count * 100 / total_count,
									title=_("Posting Overtime Entry..."),
									description=description)
			pass
		return {"messages": ret, "error": error}

@frappe.whitelist()
def download_template(file_type, branch, month, fiscal_year, upload_type, unit):
	data = frappe._dict(frappe.local.form_dict)
	writer = get_template(branch, month, fiscal_year)
	for d in get_mr_data(branch, month, fiscal_year, unit):
		row = []
		row.append(d.branch)
		row.append(d.cost_center)
		row.append(d.unit)
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

def get_mr_data(branch, month, fiscal_year, unit):
	if unit == '1':
		return frappe.db.sql('''select branch, cost_center, unit, name, person_name,
							"{fiscal_year}" as fiscal_year, "{month}" as month
							from `tabMuster Roll Employee`
							where status ="Active" and branch = {branch} 
							'''.format(branch=frappe.db.escape(branch), month=month, fiscal_year=fiscal_year), as_dict=True)

	else:
		return frappe.db.sql('''select branch, cost_center, unit, name, person_name,
					"{fiscal_year}" as fiscal_year, "{month}" as month
					from `tabMuster Roll Employee`
					where status ="Active" and branch = {branch} and unit = {unit}
					'''.format(branch=frappe.db.escape(branch), month=month, fiscal_year=fiscal_year, unit=frappe.db.escape(unit)), as_dict=True)

def get_template(branch, month, fiscal_year):
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
	
	fields = ["Branch", "Cost Center", "Unit", "Employee ID", "Employee Name", "Year", "Month"]
	total_days = monthrange(cint(fiscal_year), month_in_number[str(month)])[1]
	for day in range(cint(total_days)):
		fields.append(str(month)+'_'+str(day + 1))	
	writer = UnicodeWriter()
	writer.writerow(fields)

	return writer