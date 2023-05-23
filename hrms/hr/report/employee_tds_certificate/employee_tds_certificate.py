# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr
from operator import itemgetter

def execute(filters=None):
	validate_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	# frappe.throw('cols: {} \n data:{}'.format(columns,data))
	return columns, data, filters

def get_data( filters=None):
	data = []

	salary = """select CONVERT(a.month, UNSIGNED) as month, a.gross_pay, a.fiscal_year as fyear,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Basic Pay' and b.parent = a.name) as basic_pay,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Salary Tax' and b.parent = a.name) as tds ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'PF' and b.parent = a.name) as nppf ,
	ifnull((select b.amount from `tabSalary Detail` b where salary_component = 'Group Insurance Scheme' and b.parent = a.name),0) as gis ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Communication Allowance' and b.parent = a.name) as comm_all ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Health Contribution' and b.parent = a.name) as health,
	r.receipt_number, DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
	 from `tabSalary Slip` a, `tabTDS Receipt Entry` r
	 where a.fiscal_year = r.fiscal_year and a.month = r.month and a.docstatus = 1 and r.purpose = 'Employee Salary' and a.fiscal_year = """ + str(filters.fiscal_year)

	if filters.employee:
		salary = salary + " AND a.employee = \'" + str(filters.employee) + "\'"

	salary+=" order by r.receipt_date asc;"

	datas = frappe.db.sql(salary, as_dict=True)
	for d in datas:
		#frappe.msgprint(str(d.nppf))
		row = [get_month(d.month)+"-"+d.fyear, 
			  "Salary", 
			  d.basic_pay, 
			  round(flt(d.gross_pay) - flt(d.basic_pay) - (flt(d.comm_all) / 2), 2), 
			  round(flt(d.gross_pay)-(flt(d.comm_all) / 2),2), 
			  d.nppf,
			  d.gis,
			  flt(d.nppf)+flt(d.gis), 
			  flt(d.gross_pay) - flt(d.nppf) - flt(d.gis) - (flt(d.comm_all) / 2), 
			  d.tds if d.tds else 0, 
			  d.health,
			  d.receipt_number, 
			  d.receipt_date,
			  ""]
		data.append(row)
	#Leave Encashment 
	if filters.employee:
		fiscal_year = frappe.db.sql("select name, year_start_date, year_end_date from `tabFiscal Year` where name='{}' and disabled = 0".format(filters.fiscal_year), as_dict=True)
		if not fiscal_year:
			frappe.throw(_("missing value for <b>Fiscal Year</b> {} OR it is disabled").format(filters.fiscal_year), title="Fiscal Year missing")

		# encash_data = frappe.db.sql("select a.encashment_date AS date, a.encashment_amount, a.encashment_tax, r.receipt_number, r.receipt_date from `tabLeave Encashment` a, `tabRRCO Receipt Entries` r where a.name = r.purchase_invoice and a.employee = %s and a.docstatus = 1 and a.encashment_date between \'" + filters.fiscal_year + "-01-01\' and \'" + filters.fiscal_year + "-12-31\'", filters.employee, as_dict=True) 
		# encash_data = frappe.db.sql("select a.encashment_date, MONTH(a.encashment_date) AS month, YEAR(a.encashment_date) AS year, a.encashment_amount, a.encashment_tax, r.receipt_number, r.receipt_date from `tabLeave Encashment` a, `tabRRCO Receipt Entries` r where a.name = r.purchase_invoice and a.employee = %s and a.docstatus = 1 and a.encashment_date between \'" + filters.fiscal_year + "-01-01\' and \'" + filters.fiscal_year + "-12-31\'", filters.employee, as_dict=True) 
		encash_data = frappe.db.sql("""SELECT 
					DATE_FORMAT(a.encashment_date, '%d-%m-%Y') AS encashment_date,
						r.receipt_number, 
						MONTH(a.encashment_date) AS month, YEAR(a.encashment_date) AS year, 
						a.encashment_amount, a.encashment_tax, 
						r.receipt_number, 
						DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
					from `tabLeave Encashment` a LEFT JOIN `tabTDS Receipt Entry` r
						ON a.name = r.invoice_no
					WHERE a.employee = '"""+filters.employee+"""' and a.docstatus = 1 
						and a.encashment_date between '"""+ str(fiscal_year[0]["year_start_date"]) + """' and '""" + str(fiscal_year[0]["year_end_date"]) + """ ' """, as_dict=True) 
		# frappe.msgprint(str(encash_data))
		if encash_data:
			for a in encash_data:
				row = [
				# str(a.date)[5:7], 
				get_month(a.month)+"-"+str(a.year),
				"Leave Encashment", 
				0,
				0, 
				a.encashment_amount, 
				0, 
				0, 
				0, 
				a.encashment_amount, 
				a.encashment_tax if a.encashment_tax else 0, 
				0, 
				a.receipt_number, 
				a.receipt_date,
				a.encashment_date]
			data.append(row)

		# night_shift = frappe.db.sql("""select 
		# 					DATE_FORMAT(a.posting_date, '%d-%m-%Y') AS shift_date,
		# 					b.rate, 
		# 					b.amount,
		# 					b.no_of_shifts, 
		# 					b.shift_tax,
		# 					MONTH(a.posting_date) AS month, 
		# 					YEAR(a.posting_date) AS year	
		# 				from `tabProcess Shift Payment` a, `tabShift Payment Details` b 
		# 				where a.name = b.parent
		# 				and a.docstatus = 1
		# 				and a.posting_date between '"""+ filters.fiscal_year + """-01-01' and '""" + filters.fiscal_year + """-12-31'""", as_dict=True)
		# if night_shift:
		# 	for a in night_shift:
		# 		row = [
		# 		# str(a.date)[5:7], 
		# 		get_month(a.month)+"-"+str(a.year),
		# 		"Night Shift", 
		# 		0,
		# 		0, 
		# 		a.amount, 
		# 		0, 
		# 		0, 
		# 		0, 
		# 		a.amount, 
		# 		a.shift_tax if a.shift_tax else 0,
		# 		0, 
		# 		"", 
		# 		"",
		# 		a.shift_date]
		# 	data.append(row)
		# Overtime
		# overtime_data = frappe.db.sql("""select 
		# 			DATE_FORMAT(a.posting_date, '%d-%m-%Y') AS overtime_date,
		# 			r.receipt_number, 
		# 			MONTH(a.posting_date) AS month, YEAR(a.posting_date) AS year,
		# 			a.total_amount as overtime_amt, a.overtime_tax, 
		# 			r.receipt_number,
		# 			DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
		# 			from `tabOvertime Application` a, `tabRRCO Receipt Entries` r where a.name = r.purchase_invoice 
		# 			and a.employee = """+filters.employee+""" and a.docstatus = 1 
		# 			and a.posting_date between '"""	+ filters.fiscal_year + """-01-01' and '""" + filters.fiscal_year + """-12-31'""", as_dict=True)
		# overtime_data = frappe.db.sql("""select 
		# 			DATE_FORMAT(a.posting_date, '%d-%m-%Y') AS overtime_date,
		# 			r.receipt_number, 
		# 			MONTH(a.posting_date) AS month, YEAR(a.posting_date) AS year,
		# 			a.total_amount as overtime_amt, a.overtime_tax, 
		# 			r.receipt_number,
		# 			DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
		# 			from `tabOvertime Application` a LEFT JOIN `tabTDS Receipt Entry` r 
		# 			ON a.name = r.invoice_no
		# 			where a.employee = """+filters.employee+""" and a.docstatus = 1 
		# 			and a.posting_date between '"""	+ filters.fiscal_year + """-01-01' and '""" + filters.fiscal_year + """-12-31'""", as_dict=True)
		# if overtime_data:
		# 	for a in overtime_data:
		# 		row = [
		# 		# str(a.date)[5:7], 
		# 		get_month(a.month)+"-"+str(a.year),
		# 		"Overtime", 
		# 		0,
		# 		0, 
		# 		a.overtime_amt, 
		# 		0, 
		# 		0, 
		# 		0, 
		# 		a.overtime_amt, 
		# 		a.overtime_tax if a.overtime_tax else 0,
		# 		0, 
		# 		a.receipt_number, 
		# 		a.receipt_date,
		# 		a.overtime_date]
		# 	data.append(row)

		#Bonus
		bonus = frappe.db.sql("""
					select b.name, b.fiscal_year AS fyear,
					r.receipt_number, DATE_FORMAT(b.posting_date, '%d-%m-%Y') AS posting_date,
					MONTH(b.posting_date) AS month, 
					r.receipt_number, 
					DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
					from tabBonus b, `tabTDS Receipt Entry` r
					where b.fiscal_year = r.fiscal_year 
					and b.docstatus = 1 
					and b.posting_date between "{from_date}" and "{to_date}" 
					and r.purpose = 'Bonus' 
				""".format(from_date = str(filters.fiscal_year) + "-01-01",
					  to_date = str(filters.fiscal_year) + "-12-31"), as_dict=1)
		for b in bonus:
			amt = frappe.db.sql("""
				     	select amount, tax_amount, balance_amount  
					from `tabBonus Details` 
					where parent = %s and employee = %s
				      """, (b.name, filters.employee), as_dict=1)
			for a in amt:
				row = [
				get_month(b.month)+"-"+str(b.fyear),
				"Bonus", 
				0, 
				0, 
				a.amount, 
				0, 
				0, 
				0, 
				a.amount, 
				a.tax_amount if a.tax_amount else 0,
				0, 
				b.receipt_number, 
				b.receipt_date,
				b.posting_date]	
			data.append(row)
		#PVBA
		# pbva = frappe.db.sql("""
		# 			select b.name, b.fiscal_year  as year, b.posting_date, MONTH(b.posting_date) as month, r.receipt_number, r.receipt_date 
		# 			from tabPBVA b, `tabRRCO Receipt Entries` r
		# 			where b.fiscal_year+1 = r.fiscal_year and b.docstatus = 1 and b.posting_date between %s and %s and r.purpose = 'PBVA' 
		# 		      """, (str(filters.fiscal_year) + "-01-01", str(filters.fiscal_year) + "-12-31"), as_dict=1)
		pbva = frappe.db.sql("""
					select b.name, b.fiscal_year  as year, r.pbva,
					DATE_FORMAT(b.posting_date, '%d-%m-%Y') AS posting_date,
					MONTH(b.posting_date) as month, 
					r.receipt_number, 
					DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
					from tabPBVA b, `tabTDS Receipt Entry` r
					where b.fiscal_year = r.fiscal_year 
					and b.docstatus = 1 
					and b.posting_date between "{fdate}" and "{tdate}" 
					and r.purpose = 'PBVA' 
					and b.name = r.pbva
				      """.format(fdate= str(filters.fiscal_year) + "-01-01", tdate = str(filters.fiscal_year) + "-12-31"), as_dict=1)
		for b in pbva:
			amt = frappe.db.sql("""
				     	select amount, tax_amount, balance_amount  
					from `tabPBVA Details` 
					where parent = %s and employee = %s
				      """, (b.name, filters.employee), as_dict=1)
			for a in amt:
				row = [get_month(b.month)+"-"+str(b.year), 
					  "PBVA", 
					  0, 
					  0, 
					  a.amount, 
					  0, 
					  0, 
					  0, 
					  a.amount, 
					  a.tax_amount if a.tax_amount else 0, 
					  0, 
					  b.receipt_number, 
					  b.receipt_date,
					  b.posting_date]	
				data.append(row)
	# frappe.throw('{}'.format(data))
	return data

def validate_filters(filters):
	if not filters.fiscal_year:
		frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))
	start, end = frappe.db.get_value("Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"])
	filters.year_start = start
	filters.year_end = end

def get_columns():
	return [
		{
		  "fieldname": "month-fyear",
		  "label": "Month-Year",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "type",
		  "label": "Income Type",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "basic",
		  "label": "Basic Salary",
		  "fieldtype": "Currency",
		  "width": 150
		},
		{
		  "fieldname": "others",
		  "label": "Allowances",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "total",
		  "label": "Total Income",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "pf",
		  "label": "PF",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "gis",
		  "label": "GIS",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "totalPfGis",
		  "label": "Total of PF & GIS",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "taxable",
		  "label": "Taxable Income",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "tds",
		  "label": "TDS Amount",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "health",
		  "label": "Health",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "receipt_number",
		  "label": "RRCO Receipt No.",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "receipt_date",
		  "label": "RRCO Receipt Date",
		  "fieldtype": "Date",
		  "width": 130
		},
		{
		  "fieldname": "post_date",
		  "label": "Posting Date",
		  "fieldtype": "Data",
		  "width": 100
		},
	]

def get_month(month):
	if month == 1:
		return "Jan"
	elif month == 2:
		return "Feb"
	elif month == 3:
		return "Mar"
	elif month == 4:
		return "Apr"
	elif month == 5:
		return "May"
	elif month == 6:
		return "Jun"
	elif month == 7:
		return "Jul"
	elif month == 8:
		return "Aug"
	elif month == 9:
		return "Sep"
	elif month == 10:
		return "Oct"
	elif month == 11:
		return "Nov"
	elif month == 12:
		return "Dec"
	else:
		return "None"