# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint
from frappe.utils import cstr, add_days, date_diff, cint, flt, getdate, nowdate
from frappe import _
from frappe.utils.csvutils import UnicodeWriter
from frappe.model.document import Document
from calendar import monthrange

class UploadOvertimeEntries(Document):
	pass

@frappe.whitelist()
def get_template():
	if not frappe.has_permission("Overtime Entry", "create"):
		raise frappe.PermissionError

	args = frappe.local.form_dict
	w = UnicodeWriter()
	w = add_header(w, args)
	w = add_data(w, args)

	# write out response as a type csv
	frappe.response['result'] = cstr(w.getvalue())
	frappe.response['type'] = 'csv'
	frappe.response['doctype'] = "Overtime Entry"

def add_header(w, args):
	w.writerow(["Notes:"])
	w.writerow(["Please do not change the template headings"])
	w.writerow(["Number of hours should be Integers"])
	hd = ["Branch", "Cost Center", "Employee Type", "Employee ID", "Employee Name", "Year", "Month"]

	month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
		"Dec"].index(args.month) + 1

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
			e.branch, e.cost_center, e.etype, "\'"+str(e.name)+"\'", e.person_name, args.fiscal_year, args.month
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
                        from `tabOvertime Entry`
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
                        iw.cost_center
		from `tabMuster Roll Employee` as me, `tabEmployee Internal Work History` as iw
                where me.docstatus < 2
                and iw.parent = me.name
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
		UNION
		select distinct
                        "GEP" as etype,
                        ge.name,
                        ge.person_name,
                        iw.branch,
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
		""".format(args.branch, start_date, end_date), {"branch": args.branch}, as_dict=1)
	return employees

@frappe.whitelist()
def upload():			
	if not frappe.has_permission("Overtime Entry", "create"):
		raise frappe.PermissionError

	from frappe.utils.csvutils import read_csv_content_from_uploaded_file
	from frappe.modules import scrub

	rows = read_csv_content_from_uploaded_file()
	rows = filter(lambda x: x and any(x), rows)
	if not rows:
		msg = [_("Please select a csv file")]
		return {"messages": msg, "error": msg}
	columns = [scrub(f) for f in rows[3]]
	ret = []
	error = False

	from frappe.utils.csvutils import check_record, import_doc

	for i, row in enumerate(rows[4:]):
		if not row: continue
		try:
			row_idx = i + 4
			for j in range(8, len(row) + 1):
                                month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(row[6]) + 1
                                month = str(month) if cint(month) > 9 else str("0" + str(month))
                                day   = str(cint(j) - 7) if cint(j) > 9 else str("0" + str(cint(j) - 7))

                                old = frappe.db.get_value("Overtime Entry", {"number":str(row[3]).strip('\''), "date": str(row[5]) + '-' + str(month) + '-' + str(day), "docstatus": 1}, ["docstatus","name","number_of_hours"], as_dict=1)

                                if old:
                                        doc = frappe.get_doc("Overtime Entry", old.name)
                                        doc.db_set('number_of_hours', flt(row[j-1]))
                                
                                if not old and flt(row[j-1]) > 0:
                                        doc = frappe.new_doc("Overtime Entry")
					doc.branch          = row[0]
                                        doc.cost_center     = row[1]
                                        doc.number          = str(row[3]).strip('\'')
                                        doc.date            = str(row[5]) + '-' + str(month) + '-' + str(day)
                                        doc.number_of_hours = flt(row[j -1])
                                        
                                        if str(row[2]) == "MR":
                                                doc.employee_type = "Muster Roll Employee"
                                        elif str(row[2]) == "GEP":
                                                doc.employee_type = "DES Employee"
                                                
					if not getdate(doc.date) > getdate(nowdate()):
						doc.submit()
		except Exception, e:
			error = True
			ret.append('Error for row (#%d) %s : %s' % (row_idx,
				len(row)>1 and row[4] or "", cstr(e)))
			frappe.errprint(frappe.get_traceback())

	if error:
		frappe.db.rollback()
	else:
		frappe.db.commit()
	return {"messages": ret, "error": error}
