# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _

def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	if not data:
		return columns, data
		
	columns = get_columns(data)

	return columns, data

def get_columns(data):
	columns = [
		_("Employee") + "::150",
		_("Employee Name") + "::160",
		_("Opening Balance") + ":Currency:150",
		_("Debit") + ":Currency:150",
		_("Credit") + ":Currency:150",
		_("Closing Balance") + ":Currency:150",
	]
	return columns

def get_data(filters):
	data = []
	total_opening=total_closing=total_credit=total_debit=0.00
	adv_account = frappe.db.get_value("Company",filters.get('company'),'salary_advance_account')
	for a in frappe.db.sql("""
							select employee, employee_name
							from `tabEmployee`
							where company = '{0}' and status="Active"
							order by employee
						""".format(filters.get('company')), as_dict=True):
		closing_bal = 0.00
		open_bal = frappe.db.sql("""
							select sum(debit)-sum(credit) as opening_balance 
							from `tabGL Entry`
							where account ="{0}"
							and party = "{1}" and party_type="Employee"
							and posting_date < "{2}"
				""".format(adv_account, a.employee, filters.get('from_date')), as_dict=True)[0]
		tran = frappe.db.sql("""
							select sum(debit) as debit, sum(credit) as credit 
							from `tabGL Entry`
							where account ="{0}"
							and party = "{1}" and party_type="Employee"
							and posting_date between "{2}" and "{3}"
				""".format(adv_account, a.employee, filters.get('from_date'),  filters.get('to_date')), as_dict=True)[0]
		closing_bal = (flt(open_bal,2) + flt(tran['debit'],2)) - flt(tran['credit'],2)
		#frappe.msgprint("{}, {}, {}" .format(open_bal['opening_balance'], tran['debit'], tran['credit']))
		data.append({
			"employee": a.employee,
			"employee_name": a.employee_name,
			"opening_balance": flt(open_bal['opening_balance'],2),
			"debit": tran['debit'],
			"credit": tran['credit'],
			"closing_balance": flt(closing_bal,2)
		})
		total_opening += flt(open_bal['opening_balance'],2)
		total_debit += flt(tran['debit'],2)
		total_credit += flt(tran['credit'],2)
		total_closing += flt(closing_bal,2)
	data.append({
		"employee": "",
		"employee_name": "Total",
		"opening_balance": total_opening,
		"debit": total_debit,
		"credit": total_credit,
		"closing_balance": total_closing
	})
	return data

