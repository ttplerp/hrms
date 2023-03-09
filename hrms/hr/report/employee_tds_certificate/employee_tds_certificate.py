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
	return columns, data, filters

def get_data( filters=None):
	data = []

	salary = """select CONVERT(a.month, UNSIGNED) as month, a.gross_pay, a.fiscal_year as fyear,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Basic Pay' and b.parent = a.name) as basic_pay,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Salary Tax' and b.parent = a.name) as tds ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'PF' and b.parent = a.name) as nppf ,
	ifnull((select b.amount from `tabSalary Detail` b where salary_component = 'GIS' and b.parent = a.name),0) as gis ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Communication Allowance' and b.parent = a.name) as comm_all ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Health Contribution' and b.parent = a.name) as health,
	r.receipt_number, r.receipt_date, r.posting_date
	from `tabSalary Slip` a, `tabTDS Receipt Entry` r
	where a.fiscal_year = r.fiscal_year and a.docstatus = 1 and a.month = r.month
	and r.purpose = 'Employee Salary' and a.fiscal_year = """ + str(filters.fiscal_year)

	if filters.employee:
		salary = salary + " AND a.employee = \'" + str(filters.employee) + "\'"

	salary+=" order by r.receipt_date asc;"
	datas = frappe.db.sql(salary, as_dict=True)
	for d in datas:
		row = {
			"month-fyear":get_month(d.month)+"-"+d.fyear, 
			"type":"Salary", 
			"basic":d.basic_pay, 
			"others":round(flt(d.gross_pay) - flt(d.basic_pay) - (flt(d.comm_all) / 2), 2), 
			"total":round(flt(d.gross_pay)-(flt(d.comm_all) / 2),2), 
			"pf":d.nppf,
			"gis":d.gis,
			"totalPfGis":flt(d.nppf)+flt(d.gis), 
			"taxable":flt(d.gross_pay) - flt(d.nppf) - flt(d.gis) - (flt(d.comm_all) / 2), 
			"tds":d.tds if d.tds else 0, 
			"health":d.health,
			"receipt_number":d.receipt_number, 
			"receipt_date":d.receipt_date,
			"post_date":d.posting_date
			}
		data.append(row)
	
	#Leave Encashment 
	if filters.employee:
		encash_data = frappe.db.sql("""SELECT 
					DATE_FORMAT(a.encashment_date, '%d-%m-%Y') AS encashment_date,
						r.receipt_number, 
						MONTH(a.encashment_date) AS month, YEAR(a.encashment_date) AS year, 
						a.encashment_amount, a.encashment_tax, 
						r.receipt_number, 
						DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
					from `tabLeave Encashment` a, `tabTDS Receipt Entry` r
					WHERE a.employee = """+filters.employee+""" and a.docstatus = 1 
						and a.name = r.invoice_no
						and a.encashment_date between '"""+ filters.fiscal_year + """-01-01' and '""" + filters.fiscal_year + """-12-31'""", as_dict=True) 
		if encash_data:
			for a in encash_data:
				row = {
					"month-fyear":get_month(d.month)+"-"+d.fyear, 
					"type":"Leave Encashment", 
					"basic":0, 
					"others":0, 
					"total":a.encashment_amount, 
					"pf":0,
					"gis":0,
					"totalPfGis":0, 
					"taxable":flt(a.encashment_amount, 2), 
					"tds":a.encashment_tax if a.encashment_tax else 0, 
					"health":0,
					"receipt_number":d.receipt_number, 
					"receipt_date":d.receipt_date,
					"post_date":d.posting_date
					}
				data.append(row)
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
				row =  {
					"month-fyear":get_month(d.month)+"-"+d.fyear, 
					"type":"Bonus", 
					"basic":0, 
					"others":0, 
					"total":flt(a.amount,2), 
					"pf":0,
					"gis":0,
					"totalPfGis":0, 
					"taxable":flt(a.amount, 2), 
					"tds":a.tax_amount if a.tax_amount else 0, 
					"health":0,
					"receipt_number":d.receipt_number, 
					"receipt_date":d.receipt_date,
					"post_date":d.posting_date}
				data.append(row)
		#PVBA
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
				row =row =  {
					"month-fyear":get_month(d.month)+"-"+d.fyear, 
					"type":"PBVA", 
					"basic":0, 
					"others":0, 
					"total":flt(a.amount,2), 
					"pf":0,
					"gis":0,
					"totalPfGis":0, 
					"taxable":flt(a.amount, 2), 
					"tds":a.tax_amount if a.tax_amount else 0, 
					"health":0,
					"receipt_number":d.receipt_number, 
					"receipt_date":d.receipt_date,
					"post_date":d.posting_date}	
				data.append(row)
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
		  "fieldtype": "Date",
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