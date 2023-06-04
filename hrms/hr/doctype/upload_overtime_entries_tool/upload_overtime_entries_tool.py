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

class UploadOvertimeEntriesTool(Document):
	pass

	@frappe.whitelist()
	def upload_data(self):
		if not frappe.has_permission("Muster Roll Overtime Entry", "create"):
			raise frappe.PermissionError

		from frappe.utils.csvutils import read_csv_content_from_attached_file
		from frappe.modules import scrub
		if frappe.safe_encode(self.import_file).lower().endswith("csv".encode("utf-8")):
			from frappe.utils.csvutils import read_csv_content

			rows = read_csv_content(fcontent, False)

		elif frappe.safe_encode(self.import_file).lower().endswith("xlsx".encode("utf-8")):			
			try:
				rows = read_xlsx_file_from_attached_file(filepath = self.import_file)
			except Exception:
				frappe.throw(
					_("Unable to open attached file. Did you export it as Cxcel?"), title=_("Invalid Excel Format")
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
				row_idx = i + 6
				for j in range(7, len(row) + 1):
					month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(row[6])
					month = cint(month) + 1
					month = str(month) if cint(month) > 9 else str("0" + str(month))
					day   = cint(j)-6 if cint(j) > 9 else "0" + str(cint(j)-6)
					old = frappe.db.get_value("Muster Roll Overtime Entry", {"number":str(row[3]).strip('\''), "date": str(row[5]) + '-' + str(month) + '-' + str(day), "docstatus": 1}, ["docstatus","name","number_of_hours"], as_dict=1)

					if old:
						doc = frappe.get_doc("Muster Roll Overtime Entry", old.name)
						doc.db_set('number_of_hours', flt(row[j-1]))
					
					if not old and flt(row[j-1]) > 0:
						doc = frappe.new_doc("Muster Roll Overtime Entry")
						doc.branch          = row[0]
						doc.cost_center     = row[1]
						doc.unit 			= row[2]
						doc.number          = str(row[3]).strip('\'')
						doc.person_name     = str(row[4]).strip('\'')
						doc.date            = str(row[5]) + '-' + str(month) + '-' + str(day)
						doc.number_of_hours = flt(row[j -1])
						doc.reference		= self.name
						
						doc.employee_type = "Muster Roll Employee"
													
						if not getdate(doc.date) > getdate(nowdate()):
							doc.submit()
					successful += 1
			except Exception as e:
				failed += 1
				error = True
				ret.append('Error for row (#%d) %s : %s' % (row_idx,
					len(row)>1 and row[5] or "", cstr(e)))
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
			description = " Processing OT Of {}({}): ".format(frappe.bold(str(row[4]).strip('\'')),frappe.bold(row[3])) + "["+str(count)+"/"+str(total_count)+"]"
			frappe.publish_progress(count*100/total_count,
				title = _("Posting Overtime Entry..."),
				description = description)
			pass
		return {"messages": ret, "error": error}

@frappe.whitelist()
def download_template(file_type, branch, month, fiscal_year):
	data = frappe._dict(frappe.local.form_dict)
	writer = get_template(branch, month, fiscal_year)
	for d in get_mr_data(branch, month, fiscal_year):
		row = []
		row.append(d.branch)
		row.append(d.cost_center)
		row.append(d.unit)
		row.append(d.name)
		row.append(d.person_name)
		row.append(d.fiscal_year)
		row.append(d.month)
		writer.writerow(row)

	if file_type == "CSV":
		# download csv file
		frappe.response["result"] = cstr(writer.getvalue())
		frappe.response["type"] = "csv"
		frappe.response["doctype"] = "Muster Roll Overtime Entry"
	else:
		build_response_as_excel(writer)

def build_response_as_excel(writer):
	filename = frappe.generate_hash("", 10)
	with open(filename, "wb") as f:
		f.write(cstr(writer.getvalue()).encode("utf-8"))
	f = open(filename)
	reader = csv.reader(f)

	from frappe.utils.xlsxutils import make_xlsx

	xlsx_file = make_xlsx(reader, "Muster Roll Overtime Entry")

	f.close()
	os.remove(filename)

	# write out response as a xlsx type
	frappe.response["filename"] = "muster_roll_overtime_entries.xlsx"
	frappe.response["filecontent"] = xlsx_file.getvalue()
	frappe.response["type"] = "binary"
def get_mr_data(branch, month, fiscal_year):
	return frappe.db.sql('''select branch, cost_center, unit, name, person_name,
						 "{fiscal_year}" as fiscal_year, "{month}" as month
						from `tabMuster Roll Employee`
						where status ="Active" and branch = {branch} 
						'''.format(branch=frappe.db.escape(branch), month=month, fiscal_year=fiscal_year), as_dict=True)
	
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

def add_header(w, args):
	w.writerow(["Notes:"])
	w.writerow(["Please do not change the template headings"])
	w.writerow(["Number of hours should be Integers"])
	hd = ["Branch", "Unit", "Cost Center", "Employee ID", "Employee Name", "Year", "Month"]

	month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov","Dec"].index(args.month) + 1

	total_days = monthrange(cint(args.fiscal_year), month)[1]
	for day in range(cint(total_days)):
		hd.append(str(day + 1))	

	w.writerow(hd)
	return w

def add_data(w, args):
	#dates = get_dates(args)
	month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(args.month) + 1
	month = str(month) if cint(month) > 9 else str("0" + str(month))

	total_days = monthrange(cint(args.fiscal_year), cint(month))[1]
	start_date = str(args.fiscal_year) + '-' + str(month) + '-' + str('01')
	end_date   = str(args.fiscal_year) + '-' + str(month) + '-' + str(total_days)
		
	employees  = get_active_employees(args, start_date, end_date)
	loaded     = get_loaded_records(args, start_date, end_date)
		
	for e in employees:
		number_of_hours = ''                
		row = [
		e.branch, e.unit, e.cost_center, e.etype, "\'"+str(e.name)+"\'", e.person_name, args.fiscal_year, args.month
		]
		for day in range(cint(total_days)):
			number_of_hours = loaded.get(e.etype, frappe._dict()).get(e.name, frappe._dict()).get(day+1,'')
			row.append(number_of_hours)                
		w.writerow(row)
	return w

def get_loaded_records(args, start_date, end_date):
	loaded_list= frappe._dict()

	rl = frappe.db.sql("""
					select
							case 
								when employee_type = 'Muster Roll Employee' then 'MR'
								when employee_type = 'DES Employee' then 'GEP'
								else 'Employee'
							end as employee_type,
							number as employee,
							day(date) as day_of_date,
							sum(ifnull(number_of_hours,0)) as number_of_hours
					from `tabMuster Roll Overtime Entry`
					where branch = '{0}'
					and date between %s and %s
					and docstatus = 1                    
					group by employee_type, employee, day_of_date
			""".format(args.branch), (start_date, end_date), as_dict=1)

	for r in rl:
		loaded_list.setdefault(r.employee_type, frappe._dict()).setdefault(r.employee, frappe._dict()).setdefault(r.day_of_date,r.number_of_hours)

	return loaded_list

def get_active_employees(args, start_date, end_date):        
	employees = frappe.db.sql("""
				select distinct
						"MR" as etype,
						me.name,
						me.person_name,
						iw.branch,
			me.unit,
						iw.cost_center
		from `tabMuster Roll Employee` as me, `tabEmployee Internal Work History` as iw
				where me.docstatus < 2
				and iw.parent = me.name
				and iw.branch = '{0}'
		and me.unit = '{3}'
		and (
						('{1}' between iw.from_date and ifnull(iw.to_date,now()))
						or
						('{2}' between iw.from_date and ifnull(iw.to_date,now()))
						or
						(iw.from_date between '{1}' and '{2}')
						or
						(ifnull(iw.to_date,now()) between '{1}' and '{2}')
				)
		UNION
		select distinct
						"DES" as etype,
						ge.name,
						ge.person_name,
						iw.branch,
			'unit' as unit,
						iw.cost_center
		from `tabDES Employee` as ge, `tabEmployee Internal Work History` as iw
		where ge.docstatus < 2
				and iw.parent = ge.name
				and iw.branch = '{0}'
		and (
						('{1}' between iw.from_date and ifnull(iw.to_date,now()))
						or
						('{2}' between iw.from_date and ifnull(iw.to_date,now()))
						or
						(iw.from_date between '{1}' and '{2}')
						or
						(ifnull(iw.to_date,now()) between '{1}' and '{2}')
				)
		""".format(args.branch, start_date, end_date, args.unit), {"branch": args.branch, "unit": args.unit}, as_dict=1)

	return employees