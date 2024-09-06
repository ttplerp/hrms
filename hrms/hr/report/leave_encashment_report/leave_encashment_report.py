# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _

def execute(filters=None):
	if not filters: 
		filters = {}

	data = get_data(filters)
	columns = get_columns(data)
	
	return columns, data
	
def get_columns(data):
	columns = [
		_("Employee") + ":Link/Employee:100", 
		_("Employee Name") + "::140",
		_("Transaction No") + ":Link/Leave Encashment:140", 
		_("Date") + "::80", 
		_("TPN No") + ":Link/Leave Encashment:80",
		_("Accounts Entry") + ":Link/Journal Entry:120",
		_("Gross Amount") + ":Currency:140", 
		_("Tax Amount") + ":Currency:140", 
		_("Net Amount") + ":Currency:140",
		_("Remarks") + "::140",
		_("Balance Before") + "::80", 
		_("Days Encashed") + "::80", 
		_("Balance After") + "::80",
		_("Company") + ":Link/Company:120", 
		_("Branch") + ":Link/Branch:120", 
		_("Department") + ":Link/Department:120",
		_("Division") + ":Link/Division:120", 
		_("Section") + ":Link/Section:120",
	]
	
	return columns
	
def get_data(filters):
	conditions, filters = get_conditions(filters)

	# Following two lines added by SHIV on 31/10/2017
	enc_gl = frappe.db.get_value(doctype="HR Accounts Settings",fieldname="leave_encashment_account")
	tax_gl = frappe.db.get_value(doctype="HR Accounts Settings",fieldname="salary_tax_account")

	data = frappe.db.sql("""
		select t1.employee, t1.employee_name, t1.name, min(t1.encashment_date) as transactiondt,
		min(t3.tpn_number) as tpn_number, t2.parent voucherno,
		t1.encashment_amount,
		t1.encashment_tax,
		t1.payable_amount,
		t1.remarks,
		min(t1.leave_balance) as balance_before, min(t1.encashable_days) as encashed_days, 
		min(t1.leave_balance-t1.encashable_days) as balance_after,
		t3.company, t1.branch, t1.department, t1.division, t1.section
		from `tabLeave Encashment` t1
		left join `tabJournal Entry Account` t2
		on t2.reference_name = t1.name
		and t2.reference_type = 'Leave Encashment'
		left join `tabEmployee` t3
		on t3.employee = t1.employee                
		where t1.docstatus = 1 %(cond)s
		group by t1.employee, t1.employee_name, t1.name, t2.parent, t1.remarks
		""" % ({"enc_gl": enc_gl, "tax_gl": tax_gl, "cond": conditions}), filters)
		
	if not data:
		msgprint(_("No Data Found for month: "), raise_exception=1)
	
	return data
	
def get_conditions(filters):
	conditions = ""
	"""
	if filters.get("month"):
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
			"Dec"].index(filters["month"]) + 1
		filters["month"] = month
		conditions += " and t1.month = %(month)s"
	
	if filters.get("fiscal_year"): conditions += " and t1.fiscal_year = %(fiscal_year)s"
	if filters.get("company"): conditions += " and t1.company = %(company)s"
	"""
	if filters.get("employee"): conditions += " and t1.employee = %(employee)s"
	if filters.get("from_date") and filters.get("to_date"): conditions += " and t1.encashment_date between %(from_date)s and %(to_date)s"
	
	return conditions, filters
