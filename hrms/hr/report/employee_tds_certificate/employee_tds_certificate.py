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
	frappe.errprint(str(data))
	return columns, data, filters

def get_data( filters=None):
	data = []
    #salary arrear
	data += get_salary_arrer(filters)
	frappe.errprint(str(data))
    
	# salary 
	data += get_salary_data(filters)
	#Leave Encashment 
	data += get_leave_encashment(filters)
	#Bonus
	data += get_bonus(filters)
	#PVBA
	data += get_pbva(filters)

	return data

def get_salary_data(filters):
	data = []
	for d in frappe.db.sql('''SELECT 
								CONCAT(a.month,'-', a.fiscal_year) month_year, 
								a.gross_pay, 
								(SELECT b.amount FROM `tabSalary Detail` b WHERE b.parent = a.name AND b.salary_component = 'Basic Pay') AS basic_pay, 
								(SELECT b.amount FROM `tabSalary Detail` b WHERE b.parent = a.name AND b.salary_component = 'Salary Tax') AS tds, 
								(SELECT b.amount FROM `tabSalary Detail` b WHERE b.parent = a.name AND b.salary_component = 'PF') AS nppf, 
								COALESCE((SELECT b.amount FROM `tabSalary Detail` b WHERE b.parent = a.name AND b.salary_component = 'GIS'), 0) AS gis, 
								(SELECT b.amount FROM `tabSalary Detail` b WHERE b.parent = a.name AND b.salary_component = 'Communication Allowance') AS comm_all, 
								(SELECT b.amount FROM `tabSalary Detail` b WHERE b.parent = a.name AND b.salary_component = 'Health Contribution') AS health, 
								r.receipt_number, 
								r.receipt_date, 
								r.posting_date
							FROM `tabSalary Slip` a
							JOIN `tabTDS Receipt Entry` r ON a.fiscal_year = r.fiscal_year AND a.month = r.month
							WHERE a.docstatus = 1 AND r.purpose = 'Employee Salary'
							AND a.employee = '{employee}' 
							AND a.fiscal_year = '{fiscal_year}'
							ORDER BY r.receipt_date ASC
							'''.format(employee=filters.employee, fiscal_year = filters.fiscal_year),as_dict=1):
		data.append({
			"month_year":d.month_year, 
			"type":"Salary", 
			"basic":flt(d.basic_pay,2), 
			"others":flt(flt(d.gross_pay) - flt(d.basic_pay) - (flt(d.comm_all) / 2), 2), 
			"total":flt(flt(d.gross_pay)-(flt(d.comm_all) / 2),2), 
			"pf":flt(d.nppf,2),
			"gis":flt(d.gis,2),
			"totalPfGis":flt(flt(d.nppf)+flt(d.gis),2), 
			"taxable":flt(d.gross_pay) - flt(d.nppf) - flt(d.gis) - (flt(d.comm_all) / 2), 
			"tds":flt(d.tds,2) if d.tds else 0, 
			"health":flt(d.health,2),
			"receipt_number":d.receipt_number, 
			"receipt_date":d.receipt_date,
			"posting_date":d.posting_date
			})
	return data
def get_leave_encashment(filters):
	return frappe.db.sql("""SELECT 
								a.encashment_date AS posting_date,
								r.receipt_number,
								'Leave Encashment' as type,
								CONCAT(MONTH(a.encashment_date),'-', YEAR(a.encashment_date)) AS month_year,
								ROUND(a.encashment_amount, 2) AS total,
								ROUND(a.encashment_amount, 2) AS taxable,
								ROUND(a.encashment_tax, 2) AS tds,
								r.receipt_number,
								r.receipt_date,
								0 AS basic,
								0 AS other,
								0 AS pf,
								0 AS gis,
								0 AS totalPfGis,
								0 AS others,
								0 AS health
								FROM `tabLeave Encashment` a
								JOIN `tabTDS Receipt Entry` r ON a.name = r.invoice_no
								WHERE a.employee = '{employee}'
								AND a.docstatus = 1
								AND a.encashment_date BETWEEN '{from_date}' AND '{to_date}'
						""".format(employee=filters.employee,from_date = getdate(str(filters.fiscal_year) + "-01-01"),
					  to_date = getdate(str(filters.fiscal_year) + "-12-31")), as_dict=True) 
def get_bonus(filters):
	return frappe.db.sql("""
					SELECT CONCAT(MONTH(b.posting_date), '-', b.fiscal_year) AS month_year,
						r.receipt_number,
						b.posting_date,
						r.receipt_date,
						'Bonus' AS type,
						0 AS basic,
						0 AS others,
						ROUND(bd.amount,2) AS total,
						0 AS pf,
						0 AS gis,
						0 AS totalPfGis,
						ROUND(bd.amount,2) AS taxable,
						ROUND(ifnull(bd.tax_amount,0),2) as tds,
						0 AS health
					FROM `tabBonus` b
					JOIN `tabTDS Receipt Entry` r ON b.fiscal_year = r.fiscal_year
					JOIN `tabBonus Details` bd ON b.name = bd.parent
					WHERE b.docstatus = 1
					AND r.purpose = 'Bonus'
					AND b.posting_date BETWEEN '{from_date}' AND '{to_date}'
					AND bd.employee = '{employee}'
					AND bd.amount > 0
				""".format( fiscal_year = filters.fiscal_year, employee= filters.employee, from_date = getdate(str(filters.fiscal_year) + "-01-01"),
					to_date = getdate(str(filters.fiscal_year) + "-12-31")), as_dict=1)
def get_pbva(filters):
	return frappe.db.sql("""SELECT 
									ROUND(IFNULL(bd.amount,0),2) AS total, 
									ROUND(IFNULL(bd.amount,0),2) AS taxable, 
									ROUND(IFNULL(bd.tax_amount,0),2) as tds,
									CONCAT(MONTH(b.posting_date),'-',
									b.fiscal_year) AS month_year,
									'PBVA' AS type, 
									0 as basic, 
									0 as others, 
									0 AS pf, 
									0 AS gis, 
									0 AS totalPfGis, 
									0 AS health,
									r.receipt_date,	
									r.receipt_number,
									b.posting_date
								FROM tabPBVA b
								INNER JOIN `tabTDS Receipt Entry` r ON b.fiscal_year = r.fiscal_year AND r.purpose = 'PBVA'
								LEFT JOIN `tabPBVA Details` bd ON b.name = bd.parent AND bd.employee = '{employee}'
								WHERE b.docstatus = 1 AND bd.amount > 0 
								AND b.posting_date BETWEEN '{from_date}' AND '{to_date}'
				      """.format( employee = filters.employee, fiscal_year=filters.fiscal_year, from_date = getdate(str(filters.fiscal_year) + "-01-01"),
					  to_date = getdate(str(filters.fiscal_year) + "-12-31")), as_dict=1)
 
def get_salary_arrer(filters):
   
    return frappe.db.sql("""
SELECT 
    CONCAT(t5.month,'-', t5.fiscal_year) AS month_year, 
      (
        SELECT posting_date 
        FROM `tabSalary Arrear Payment`  
        WHERE company = 'State Mining Corporation Ltd'AND posting_date BETWEEN '{from_date}' AND '{to_date}' limit 1
    ) AS posting_date,
    t4.arrear_basic_pay AS basic,
    t4.arrear_pf AS pf,
    ifnull(
        sum(t4.arrear_corporate_allowance+t4.arrear_contract_allowance+t4.arrear_officiating_allowance+t4.arrear_mpi+fixed_allowance ) + t4.arrear_basic_pay,0)
        AS total,
  
	ifnull(
     sum(t4.arrear_corporate_allowance+t4.arrear_contract_allowance+t4.arrear_officiating_allowance+t4.arrear_mpi+fixed_allowance),0)
     AS others, 
	0 AS gis, 
	ifnull(t4.arrear_pf,0 ) AS totalPfGis, 
	t4.arrear_hc AS health,
	ifnull(sum(t4.arrear_corporate_allowance+t4.arrear_contract_allowance+t4.arrear_officiating_allowance+t4.arrear_mpi+fixed_allowance ) +(t4.arrear_basic_pay)-(t4.arrear_pf),0) AS taxable,
    ifnull(t4.arrear_salary_tax,0) AS tds,
    'Salary Arrear' AS type,
    tds_receipt_number AS receipt_number,
    tds_receipt_date AS receipt_date
  
    
FROM 
    `tabSalary Arrear Payment Item` t4 
Right JOIN 
    `tabTDS Receipt Update` t5 ON t5.purpose = 'Salary Arrear' 
WHERE 
    t4.employee = '{employee}' and t5.docstatus = 1
    
    """.format(employee = filters.employee,fiscal_year=filters.fiscal_year,from_date = getdate(str(filters.fiscal_year) + "-01-01"),
					  to_date = getdate(str(filters.fiscal_year) + "-12-31")),as_dict=True)

	
def validate_filters(filters):
	if not filters.fiscal_year:
		frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))
	start, end = frappe.db.get_value("Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"])
	filters.year_start = start
	filters.year_end = end


def get_columns():
	return [
		{
		  "fieldname": "month_year",
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
		  "fieldname": "posting_date",
		  "label": "Posting Date",
		  "fieldtype": "Date",
		  "width": 130
		},
	]
