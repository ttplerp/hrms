# # Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# # For license information, please see license.txt

# from __future__ import unicode_literals
# import frappe
# from frappe import _
# from frappe.utils import flt, getdate, formatdate, cstr
# from operator import itemgetter

# def execute(filters=None):
# 	validate_filters(filters)
# 	columns = get_columns()
# 	data = get_data(filters)
# 	# frappe.throw('cols: {} \n data:{}'.format(columns,data))
# 	return columns, data, filters

# def get_data(filters=None):
# 	data = []

# 	receipt_cond = ""
# 	if filters.get("receipt_date"):
# 		receipt_cond = " AND r.receipt_date = '{0}'".format(filters.receipt_date)

# 	# salary = """select CONVERT(a.month, UNSIGNED) as month, a.gross_pay, a.fiscal_year as fyear,
# 	# (select b.amount from `tabSalary Detail` b where b.salary_component = 'Basic Pay' and b.parent = a.name) as basic_pay,
# 	# (select b.amount from `tabSalary Detail` b where b.salary_component = 'Salary Tax' and b.parent = a.name) as tds ,
# 	# (select b.amount from `tabSalary Detail` b where b.salary_component = 'PF' and b.parent = a.name) as nppf ,
# 	# ifnull((select b.amount from `tabSalary Detail` b where b.salary_component = 'Group Insurance Scheme' and b.parent = a.name),0) as gis ,
# 	# (select b.amount from `tabSalary Detail` b where b.salary_component = 'Communication Allowance' and b.parent = a.name) as comm_all ,
# 	# (select b.amount from `tabSalary Detail` b where b.salary_component = 'Health Contribution' and b.parent = a.name) as health,
# 	# r.receipt_number, DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
# 	#  from `tabSalary Slip` a JOIN `tabTDS Receipt Entry` r
# 	#  ON a.fiscal_year = r.fiscal_year and a.month = r.month and a.docstatus = 1 and r.purpose = 'Employee Salary' and a.fiscal_year = \'""" + str(filters.fiscal_year) + "\'"

# 	salary = """select 
# 		CONVERT(a.month, UNSIGNED) as month, 
# 		a.gross_pay, 
# 		a.fiscal_year as fyear,
# 		(select b.amount from `tabSalary Detail` b where b.salary_component = 'Basic Pay' and b.parent = a.name) as basic_pay,
# 		(select b.amount from `tabSalary Detail` b where b.salary_component = 'Salary Tax' and b.parent = a.name) as tds,
# 		(select b.amount from `tabSalary Detail` b where b.salary_component = 'PF' and b.parent = a.name) as nppf,
# 		ifnull((select b.amount from `tabSalary Detail` b where b.salary_component = 'Group Insurance Scheme' and b.parent = a.name),0) as gis,
# 		(select b.amount from `tabSalary Detail` b where b.salary_component = 'Communication Allowance' and b.parent = a.name) as comm_all,
# 		(select b.amount from `tabSalary Detail` b where b.salary_component = 'Health Contribution' and b.parent = a.name) as health,
# 		r.receipt_number,
# 		DATE_FORMAT(r.receipt_date, '%Y-%m-%d') AS receipt_date
# 	from `tabSalary Slip` a
# 	JOIN `tabTDS Receipt Entry` r
# 		ON a.fiscal_year = r.fiscal_year
# 		AND a.month = r.month
# 		AND a.docstatus = 1
# 		AND r.purpose = 'Employee Salary'
# 		AND a.fiscal_year = '{fyear}'
# 		{receipt_cond}
# 	""".format(
# 		fyear=filters.fiscal_year,
# 		receipt_cond=receipt_cond
# 	)

# 	if filters.employee:
# 		salary = salary + " AND a.employee = \'" + str(filters.employee) + "\'"

# 	receipt_cond = ""
# 	if filters.get("receipt_date"):
# 		receipt_cond = " AND r.receipt_date = '{0}'".format(filters.receipt_date)	

# 	salary+=" order by r.receipt_date asc;"

# 	# frappe.throw(salary)
# 	datas = frappe.db.sql(salary, as_dict=True)
# 	for d in datas:
# 		#frappe.msgprint(str(d.nppf))
# 		row = [get_month(d.month)+"-"+d.fyear, 
# 			  "Salary", 
# 			  d.basic_pay, 
# 			  round(flt(d.gross_pay) - flt(d.basic_pay) - (flt(d.comm_all) / 2), 2), 
# 			  round(flt(d.gross_pay)-(flt(d.comm_all) / 2),2), 
# 			  d.nppf,
# 			  d.gis,
# 			  flt(d.nppf)+flt(d.gis), 
# 			  flt(d.gross_pay) - flt(d.nppf) - flt(d.gis) - (flt(d.comm_all) / 2), 
# 			  d.tds if d.tds else 0, 
# 			  d.health,
# 			  d.receipt_number, 
# 			  d.receipt_date,
# 			  ""]
# 		data.append(row)
# 	#Leave Encashment 
# 	if filters.employee:
# 		fiscal_year = frappe.db.sql("select name, year_start_date, year_end_date from `tabFiscal Year` where name='{}' and disabled = 0".format(filters.fiscal_year), as_dict=True)
# 		if not fiscal_year:
# 			frappe.throw(_("missing value for <b>Fiscal Year</b> {} OR it is disabled").format(filters.fiscal_year), title="Fiscal Year missing")

# 		# encash_data = frappe.db.sql("select a.encashment_date AS date, a.encashment_amount, a.encashment_tax, r.receipt_number, r.receipt_date from `tabLeave Encashment` a, `tabRRCO Receipt Entries` r where a.name = r.purchase_invoice and a.employee = %s and a.docstatus = 1 and a.encashment_date between \'" + filters.fiscal_year + "-01-01\' and \'" + filters.fiscal_year + "-12-31\'", filters.employee, as_dict=True) 
# 		# encash_data = frappe.db.sql("select a.encashment_date, MONTH(a.encashment_date) AS month, YEAR(a.encashment_date) AS year, a.encashment_amount, a.encashment_tax, r.receipt_number, r.receipt_date from `tabLeave Encashment` a, `tabRRCO Receipt Entries` r where a.name = r.purchase_invoice and a.employee = %s and a.docstatus = 1 and a.encashment_date between \'" + filters.fiscal_year + "-01-01\' and \'" + filters.fiscal_year + "-12-31\'", filters.employee, as_dict=True)
		
# 		# encash_data = frappe.db.sql("""SELECT 
# 		# 			DATE_FORMAT(a.encashment_date, '%d-%m-%Y') AS encashment_date,
# 		# 				r.receipt_number, 
# 		# 				MONTH(a.encashment_date) AS month, YEAR(a.encashment_date) AS year, 
# 		# 				a.encashment_amount, a.encashment_tax, 
# 		# 				r.receipt_number, 
# 		# 				DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
# 		# 			from `tabLeave Encashment` a LEFT JOIN `tabTDS Receipt Entry` r
# 		# 				ON a.name = r.invoice_no
# 		# 			WHERE a.employee = '"""+filters.employee+"""' and a.docstatus = 1 
# 		# 				and a.encashment_date between '"""+ str(fiscal_year[0]["year_start_date"]) + """' and '""" + str(fiscal_year[0]["year_end_date"]) + """ ' """, as_dict=True) 
# 		# frappe.msgprint(str(encash_data))

# 		encash_data = frappe.db.sql("""
# 			SELECT
# 				DATE_FORMAT(a.encashment_date, '%d-%m-%Y') AS encashment_date,
# 				MONTH(a.encashment_date) AS month,
# 				YEAR(a.encashment_date) AS year,
# 				a.encashment_amount,
# 				a.encashment_tax,
# 				r.receipt_number,
# 				DATE_FORMAT(r.receipt_date, '%Y-%m-%d') AS receipt_date
# 			FROM `tabLeave Encashment` a
# 			LEFT JOIN `tabTDS Receipt Entry` r
# 				ON a.name = r.invoice_no
# 			WHERE a.employee = '{employee}'
# 				AND a.docstatus = 1
# 				AND a.encashment_date BETWEEN '{from_date}' AND '{to_date}'
# 				{receipt_cond}
# 		""".format(
# 			employee=filters.employee,
# 			from_date=fiscal_year[0].year_start_date,
# 			to_date=fiscal_year[0].year_end_date,
# 			receipt_cond=receipt_cond
# 		), as_dict=True)

# 		if encash_data:
# 			for a in encash_data:
# 				row = [
# 				# str(a.date)[5:7], 
# 				get_month(a.month)+"-"+str(a.year),
# 				"Leave Encashment", 
# 				0,
# 				0, 
# 				a.encashment_amount, 
# 				0, 
# 				0, 
# 				0, 
# 				a.encashment_amount, 
# 				a.encashment_tax if a.encashment_tax else 0, 
# 				0, 
# 				a.receipt_number, 
# 				a.receipt_date,
# 				a.receipt_date,
# 				a.encashment_date]
# 			data.append(row)

# 		# night_shift = frappe.db.sql("""select 
# 		# 					DATE_FORMAT(a.posting_date, '%d-%m-%Y') AS shift_date,
# 		# 					b.rate, 
# 		# 					b.amount,
# 		# 					b.no_of_shifts, 
# 		# 					b.shift_tax,
# 		# 					MONTH(a.posting_date) AS month, 
# 		# 					YEAR(a.posting_date) AS year	
# 		# 				from `tabProcess Shift Payment` a, `tabShift Payment Details` b 
# 		# 				where a.name = b.parent
# 		# 				and a.docstatus = 1
# 		# 				and a.posting_date between '"""+ filters.fiscal_year + """-01-01' and '""" + filters.fiscal_year + """-12-31'""", as_dict=True)
# 		# if night_shift:
# 		# 	for a in night_shift:
# 		# 		row = [
# 		# 		# str(a.date)[5:7], 
# 		# 		get_month(a.month)+"-"+str(a.year),
# 		# 		"Night Shift", 
# 		# 		0,
# 		# 		0, 
# 		# 		a.amount, 
# 		# 		0, 
# 		# 		0, 
# 		# 		0, 
# 		# 		a.amount, 
# 		# 		a.shift_tax if a.shift_tax else 0,
# 		# 		0, 
# 		# 		"", 
# 		# 		"",
# 		# 		a.shift_date]
# 		# 	data.append(row)
# 		# Overtime
# 		# overtime_data = frappe.db.sql("""select 
# 		# 			DATE_FORMAT(a.posting_date, '%d-%m-%Y') AS overtime_date,
# 		# 			r.receipt_number, 
# 		# 			MONTH(a.posting_date) AS month, YEAR(a.posting_date) AS year,
# 		# 			a.total_amount as overtime_amt, a.overtime_tax, 
# 		# 			r.receipt_number,
# 		# 			DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
# 		# 			from `tabOvertime Application` a, `tabRRCO Receipt Entries` r where a.name = r.purchase_invoice 
# 		# 			and a.employee = """+filters.employee+""" and a.docstatus = 1 
# 		# 			and a.posting_date between '"""	+ filters.fiscal_year + """-01-01' and '""" + filters.fiscal_year + """-12-31'""", as_dict=True)
# 		# overtime_data = frappe.db.sql("""select 
# 		# 			DATE_FORMAT(a.posting_date, '%d-%m-%Y') AS overtime_date,
# 		# 			r.receipt_number, 
# 		# 			MONTH(a.posting_date) AS month, YEAR(a.posting_date) AS year,
# 		# 			a.total_amount as overtime_amt, a.overtime_tax, 
# 		# 			r.receipt_number,
# 		# 			DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
# 		# 			from `tabOvertime Application` a LEFT JOIN `tabTDS Receipt Entry` r 
# 		# 			ON a.name = r.invoice_no
# 		# 			where a.employee = """+filters.employee+""" and a.docstatus = 1 
# 		# 			and a.posting_date between '"""	+ filters.fiscal_year + """-01-01' and '""" + filters.fiscal_year + """-12-31'""", as_dict=True)
# 		# if overtime_data:
# 		# 	for a in overtime_data:
# 		# 		row = [
# 		# 		# str(a.date)[5:7], 
# 		# 		get_month(a.month)+"-"+str(a.year),
# 		# 		"Overtime", 
# 		# 		0,
# 		# 		0, 
# 		# 		a.overtime_amt, 
# 		# 		0, 
# 		# 		0, 
# 		# 		0, 
# 		# 		a.overtime_amt, 
# 		# 		a.overtime_tax if a.overtime_tax else 0,
# 		# 		0, 
# 		# 		a.receipt_number, 
# 		# 		a.receipt_date,
# 		# 		a.overtime_date]
# 		# 	data.append(row)

# 		#Bonus
# 		# bonus = frappe.db.sql("""
# 		# 			select b.name, b.fiscal_year AS fyear,
# 		# 			r.receipt_number, DATE_FORMAT(b.posting_date, '%d-%m-%Y') AS posting_date,
# 		# 			MONTH(b.posting_date) AS month, 
# 		# 			r.receipt_number, 
# 		# 			DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
# 		# 			from tabBonus b, `tabTDS Receipt Entry` r
# 		# 			where b.fiscal_year = r.fiscal_year 
# 		# 			and b.docstatus = 1 
# 		# 			and b.posting_date between "{from_date}" and "{to_date}" 
# 		# 			and r.purpose = 'Bonus' 
# 		# 		""".format(from_date = str(filters.fiscal_year) + "-01-01",
# 		# 			  to_date = str(filters.fiscal_year) + "-12-31"), as_dict=1)

# 		bonus = frappe.db.sql("""
# 			SELECT
# 				b.name,
# 				b.fiscal_year AS fyear,
# 				MONTH(b.posting_date) AS month,
# 				r.receipt_number,
# 				DATE_FORMAT(r.receipt_date, '%Y-%m-%d') AS receipt_date,
# 				DATE_FORMAT(b.posting_date, '%d-%m-%Y') AS posting_date
# 			FROM tabBonus b
# 			JOIN `tabTDS Receipt Entry` r
# 				ON b.fiscal_year = r.fiscal_year
# 			WHERE b.docstatus = 1
# 				AND r.purpose = 'Bonus'
# 				AND b.posting_date BETWEEN '{from_date}' AND '{to_date}'
# 				{receipt_cond}
# 		""".format(
# 			from_date=str(filters.fiscal_year) + "-01-01",
# 			to_date=str(filters.fiscal_year) + "-12-31",
# 			receipt_cond=receipt_cond
# 		), as_dict=True)

# 		for b in bonus:
# 			amt = frappe.db.sql("""
# 				     	select amount, tax_amount, balance_amount  
# 					from `tabBonus Details` 
# 					where parent = %s and employee = %s
# 				      """, (b.name, filters.employee), as_dict=1)
# 			for a in amt:
# 				row = [
# 				get_month(b.month)+"-"+str(b.fyear),
# 				"Bonus", 
# 				0, 
# 				0, 
# 				a.amount, 
# 				0, 
# 				0, 
# 				0, 
# 				a.amount, 
# 				a.tax_amount if a.tax_amount else 0,
# 				0, 
# 				b.receipt_number, 
# 				b.receipt_date,
# 				b.receipt_date,
# 				b.posting_date]	
# 			data.append(row)
# 		#PVBA
# 		# pbva = frappe.db.sql("""
# 		# 			select b.name, b.fiscal_year  as year, b.posting_date, MONTH(b.posting_date) as month, r.receipt_number, r.receipt_date 
# 		# 			from tabPBVA b, `tabRRCO Receipt Entries` r
# 		# 			where b.fiscal_year+1 = r.fiscal_year and b.docstatus = 1 and b.posting_date between %s and %s and r.purpose = 'PBVA' 
# 		# 		      """, (str(filters.fiscal_year) + "-01-01", str(filters.fiscal_year) + "-12-31"), as_dict=1)

# 		# pbva = frappe.db.sql("""
# 		# 			select b.name, b.fiscal_year  as year, r.pbva,
# 		# 			DATE_FORMAT(b.posting_date, '%d-%m-%Y') AS posting_date,
# 		# 			MONTH(b.posting_date) as month, 
# 		# 			r.receipt_number, 
# 		# 			DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
# 		# 			from tabPBVA b, `tabTDS Receipt Entry` r
# 		# 			where b.fiscal_year = r.fiscal_year 
# 		# 			and b.docstatus = 1 
# 		# 			and b.posting_date between "{fdate}" and "{tdate}" 
# 		# 			and r.purpose = 'PBVA' 
# 		# 			and b.name = r.pbva
# 		# 		      """.format(fdate= str(filters.fiscal_year) + "-01-01", tdate = str(filters.fiscal_year) + "-12-31"), as_dict=1)

# 		pbva = frappe.db.sql("""
# 			SELECT
# 				b.name,
# 				b.fiscal_year AS year,
# 				MONTH(b.posting_date) AS month,
# 				DATE_FORMAT(b.posting_date, '%d-%m-%Y') AS posting_date,
# 				r.receipt_number,
# 				DATE_FORMAT(r.receipt_date, '%Y-%m-%d') AS receipt_date
# 			FROM tabPBVA b
# 			JOIN `tabTDS Receipt Entry` r
# 				ON b.name = r.pbva
# 			WHERE b.docstatus = 1
# 				AND r.purpose = 'PBVA'
# 				AND b.posting_date BETWEEN '{from_date}' AND '{to_date}'
# 				{receipt_cond}
# 		""".format(
# 			from_date=str(filters.fiscal_year) + "-01-01",
# 			to_date=str(filters.fiscal_year) + "-12-31",
# 			receipt_cond=receipt_cond
# 		), as_dict=True)

# 		for b in pbva:
# 			amt = frappe.db.sql("""
# 				     	select amount, tax_amount, balance_amount  
# 					from `tabPBVA Details` 
# 					where parent = %s and employee = %s
# 				      """, (b.name, filters.employee), as_dict=1)
# 			for a in amt:
# 				row = [get_month(b.month)+"-"+str(b.year), 
# 					  "PBVA", 
# 					  0, 
# 					  0, 
# 					  a.amount, 
# 					  0, 
# 					  0, 
# 					  0, 
# 					  a.amount, 
# 					  a.tax_amount if a.tax_amount else 0, 
# 					  0, 
# 					  b.receipt_number, 
# 					  b.receipt_date,
# 					  b.posting_date]	
# 				data.append(row)
# 	# frappe.throw('{}'.format(data))
# 	return data

# def validate_filters(filters):
# 	if not filters.fiscal_year:
# 		frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))
# 	start, end = frappe.db.get_value("Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"])
# 	filters.year_start = start
# 	filters.year_end = end

# def get_columns():
# 	return [
# 		{
# 		  "fieldname": "month-fyear",
# 		  "label": "Month-Year",
# 		  "fieldtype": "Data",
# 		  "width": 100
# 		},
# 		{
# 		  "fieldname": "type",
# 		  "label": "Income Type",
# 		  "fieldtype": "Data",
# 		  "width": 100
# 		},
# 		{
# 		  "fieldname": "basic",
# 		  "label": "Basic Salary",
# 		  "fieldtype": "Currency",
# 		  "width": 150
# 		},
# 		{
# 		  "fieldname": "others",
# 		  "label": "Allowances",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "total",
# 		  "label": "Total Income",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "pf",
# 		  "label": "PF",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "gis",
# 		  "label": "GIS",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "totalPfGis",
# 		  "label": "Total of PF & GIS",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "taxable",
# 		  "label": "Taxable Income",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "tds",
# 		  "label": "TDS Amount",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "health",
# 		  "label": "Health",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "receipt_number",
# 		  "label": "RRCO Receipt No.",
# 		  "fieldtype": "Data",
# 		  "width": 150
# 		},
# 		{
# 		  "fieldname": "receipt_date",
# 		  "label": "RRCO Receipt Date",
# 		  "fieldtype": "Date",
# 		  "width": 130
# 		},
# 		{
# 		  "fieldname": "post_date",
# 		  "label": "Posting Date",
# 		  "fieldtype": "Data",
# 		  "width": 100
# 		},
# 	]

# def get_month(month):
# 	if month == 1:
# 		return "Jan"
# 	elif month == 2:
# 		return "Feb"
# 	elif month == 3:
# 		return "Mar"
# 	elif month == 4:
# 		return "Apr"
# 	elif month == 5:
# 		return "May"
# 	elif month == 6:
# 		return "Jun"
# 	elif month == 7:
# 		return "Jul"
# 	elif month == 8:
# 		return "Aug"
# 	elif month == 9:
# 		return "Sep"
# 	elif month == 10:
# 		return "Oct"
# 	elif month == 11:
# 		return "Nov"
# 	elif month == 12:
# 		return "Dec"
# 	else:
# 		return "None"





from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate

# ---------------------------------------------------------
# MAIN EXECUTE
# ---------------------------------------------------------
def execute(filters=None):
    validate_filters(filters)
    columns = get_columns()
    data = get_data(filters)
    return columns, data


# ---------------------------------------------------------
# VALIDATE FILTERS
# ---------------------------------------------------------
def validate_filters(filters):
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("From Date and To Date are required"))
    if getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw(_("From Date cannot be greater than To Date"))


# ---------------------------------------------------------
# COLUMNS
# ---------------------------------------------------------
def get_columns():
    return [
        {"label": "Month-Year", "fieldtype": "Data", "width": 110},
        {"label": "Income Type", "fieldtype": "Data", "width": 130},
        {"label": "Basic Salary", "fieldtype": "Currency", "width": 130},
        {"label": "Allowances", "fieldtype": "Currency", "width": 120},
        {"label": "Total Income", "fieldtype": "Currency", "width": 120},
        {"label": "PF", "fieldtype": "Currency", "width": 100},
        {"label": "GIS", "fieldtype": "Currency", "width": 100},
        {"label": "Total PF & GIS", "fieldtype": "Currency", "width": 130},
        {"label": "Taxable Income", "fieldtype": "Currency", "width": 130},
        {"label": "TDS", "fieldtype": "Currency", "width": 100},
        {"label": "Health", "fieldtype": "Currency", "width": 100},
        {"label": "Receipt No", "fieldtype": "Data", "width": 150},
        {"label": "Receipt Date", "fieldtype": "Date", "width": 120},
        {"label": "Posting Date", "fieldtype": "Date", "width": 120},
    ]


# ---------------------------------------------------------
# MONTH UTILITY
# ---------------------------------------------------------
def get_month(month):
    return ["Jan","Feb","Mar","Apr","May","Jun",
            "Jul","Aug","Sep","Oct","Nov","Dec"][month-1]


# ---------------------------------------------------------
# FETCH DATA
# ---------------------------------------------------------
def get_data(filters):
    data = []

    from_date = filters.from_date
    to_date = filters.to_date

    # -------------------- SALARY --------------------
    salary_sql = f"""
        SELECT 
            MONTH(sd.from_date) AS month,
            YEAR(sd.from_date) AS year,
            ss.gross_pay,
            SUM(CASE WHEN sd.salary_component = 'Basic Pay' THEN sd.amount ELSE 0 END) AS basic_pay,
            SUM(CASE WHEN sd.salary_component = 'Salary Tax' THEN sd.amount ELSE 0 END) AS tds,
            SUM(CASE WHEN sd.salary_component = 'PF' THEN sd.amount ELSE 0 END) AS nppf,
            SUM(CASE WHEN sd.salary_component = 'Group Insurance Scheme' THEN sd.amount ELSE 0 END) AS gis,
            SUM(CASE WHEN sd.salary_component = 'Communication Allowance' THEN sd.amount ELSE 0 END) AS comm_all,
            SUM(CASE WHEN sd.salary_component = 'Health Contribution' THEN sd.amount ELSE 0 END) AS health,
            r.receipt_number,
            DATE_FORMAT(r.receipt_date, '%%Y-%%m-%%d') AS receipt_date,
            ss.name AS salary_slip
        FROM `tabSalary Slip` ss
        JOIN `tabSalary Detail` sd ON sd.parent = ss.name
        LEFT JOIN `tabTDS Receipt Entry` r
            ON r.invoice_no = ss.name AND r.purpose = 'Employee Salary'
        WHERE ss.docstatus = 1
          AND sd.from_date >= '{from_date}'
          AND sd.to_date <= '{to_date}'
    """
    if filters.get("employee"):
        salary_sql += f" AND ss.employee = '{filters.employee}'"

    salary_sql += " GROUP BY ss.name ORDER BY sd.from_date ASC"

    salaries = frappe.db.sql(salary_sql, as_dict=True)
    for d in salaries:
        row = [
            get_month(d.month) + "-" + str(d.year),
            "Salary",
            d.basic_pay or 0,
            round(flt(d.gross_pay) - flt(d.basic_pay) - (flt(d.comm_all) / 2), 2),
            round(flt(d.gross_pay) - (flt(d.comm_all) / 2), 2),
            d.nppf or 0,
            d.gis or 0,
            flt(d.nppf) + flt(d.gis),
            flt(d.gross_pay) - flt(d.nppf) - flt(d.gis) - (flt(d.comm_all) / 2),
            d.tds or 0,
            d.health or 0,
            d.receipt_number or "",
            d.receipt_date or "",
            ""
        ]
        data.append(row)

    # -------------------- LEAVE ENCASHMENT --------------------
    if filters.get("employee"):
        encash_sql = f"""
            SELECT 
                MONTH(a.encashment_date) AS month,
                YEAR(a.encashment_date) AS year,
                a.encashment_amount,
                a.encashment_tax,
                r.receipt_number,
                DATE_FORMAT(r.receipt_date, '%%Y-%%m-%%d') AS receipt_date,
                a.encashment_date
            FROM `tabLeave Encashment` a
            LEFT JOIN `tabTDS Receipt Entry` r ON r.invoice_no = a.name
            WHERE a.employee = '{filters.employee}'
              AND a.docstatus = 1
              AND a.encashment_date BETWEEN '{from_date}' AND '{to_date}'
        """
        encashments = frappe.db.sql(encash_sql, as_dict=True)
        for a in encashments:
            row = [
                get_month(a.month) + "-" + str(a.year),
                "Leave Encashment",
                0, 0,
                a.encashment_amount,
                0, 0, 0,
                a.encashment_amount,
                a.encashment_tax or 0,
                0,
                a.receipt_number or "",
                a.receipt_date or "",
                a.encashment_date
            ]
            data.append(row)

    # -------------------- BONUS --------------------
    bonus_sql = f"""
        SELECT 
            b.name,
            MONTH(b.posting_date) AS month,
            YEAR(b.posting_date) AS year,
            r.receipt_number,
            DATE_FORMAT(r.receipt_date, '%%Y-%%m-%%d') AS receipt_date,
            DATE_FORMAT(b.posting_date, '%%Y-%%m-%%d') AS posting_date
        FROM `tabBonus` b
        LEFT JOIN `tabTDS Receipt Entry` r ON r.pbva IS NULL AND r.invoice_no IS NULL
        WHERE b.docstatus = 1
          AND b.posting_date BETWEEN '{from_date}' AND '{to_date}'
    """
    if filters.get("employee"):
        bonus_sql += f" AND EXISTS (SELECT 1 FROM `tabBonus Details` bd WHERE bd.parent=b.name AND bd.employee='{filters.employee}')"

    bonuses = frappe.db.sql(bonus_sql, as_dict=True)
    for b in bonuses:
        amounts = frappe.db.sql("""
            SELECT amount, tax_amount 
            FROM `tabBonus Details` 
            WHERE parent=%s AND employee=%s
        """, (b.name, filters.employee), as_dict=True)
        for a in amounts:
            row = [
                get_month(b.month) + "-" + str(b.year),
                "Bonus",
                0, 0,
                a.amount,
                0, 0, 0,
                a.amount,
                a.tax_amount or 0,
                0,
                b.receipt_number or "",
                b.receipt_date or "",
                b.posting_date
            ]
            data.append(row)

    # -------------------- PBVA --------------------
    pbva_sql = f"""
        SELECT 
            b.name,
            MONTH(b.posting_date) AS month,
            YEAR(b.posting_date) AS year,
            r.pbva,
            DATE_FORMAT(b.posting_date, '%%Y-%%m-%%d') AS posting_date,
            r.receipt_number,
            DATE_FORMAT(r.receipt_date, '%%Y-%%m-%%d') AS receipt_date
        FROM tabPBVA b
        LEFT JOIN `tabTDS Receipt Entry` r ON r.pbva = b.name
        WHERE b.docstatus = 1
          AND b.posting_date BETWEEN '{from_date}' AND '{to_date}'
    """
    if filters.get("employee"):
        pbva_sql += f" AND EXISTS (SELECT 1 FROM `tabPBVA Details` pd WHERE pd.parent=b.name AND pd.employee='{filters.employee}')"

    pbvas = frappe.db.sql(pbva_sql, as_dict=True)
    for b in pbvas:
        amounts = frappe.db.sql("""
            SELECT amount, tax_amount 
            FROM `tabPBVA Details` 
            WHERE parent=%s AND employee=%s
        """, (b.name, filters.employee), as_dict=True)
        for a in amounts:
            row = [
                get_month(b.month) + "-" + str(b.year),
                "PBVA",
                0, 0,
                a.amount,
                0, 0, 0,
                a.amount,
                a.tax_amount or 0,
                0,
                b.receipt_number or "",
                b.receipt_date or "",
                b.posting_date
            ]
            data.append(row)

    return data





























# # Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# # For license information, please see license.txt

# from __future__ import unicode_literals
# import frappe
# from frappe import _
# from frappe.utils import flt, getdate, formatdate, cstr
# from operator import itemgetter

# def execute(filters=None):
# 	validate_filters(filters)
# 	columns = get_columns()
# 	data = get_data(filters)
# 	# frappe.throw('cols: {} \n data:{}'.format(columns,data))
# 	return columns, data, filters

# def get_data(filters=None):
# 	data = []

# 	# salary = """select CONVERT(a.month, UNSIGNED) as month, a.gross_pay, a.fiscal_year as fyear,
# 	# (select b.amount from `tabSalary Detail` b where b.salary_component = 'Basic Pay' and b.parent = a.name) as basic_pay,
# 	# (select b.amount from `tabSalary Detail` b where b.salary_component = 'Salary Tax' and b.parent = a.name) as tds ,
# 	# (select b.amount from `tabSalary Detail` b where b.salary_component = 'PF' and b.parent = a.name) as nppf ,
# 	# ifnull((select b.amount from `tabSalary Detail` b where b.salary_component = 'Group Insurance Scheme' and b.parent = a.name),0) as gis ,
# 	# (select b.amount from `tabSalary Detail` b where b.salary_component = 'Communication Allowance' and b.parent = a.name) as comm_all ,
# 	# (select b.amount from `tabSalary Detail` b where b.salary_component = 'Health Contribution' and b.parent = a.name) as health,
# 	# r.receipt_number, DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
# 	#  from `tabSalary Slip` a JOIN `tabTDS Receipt Entry` r
# 	#  ON a.fiscal_year = r.fiscal_year and a.month = r.month and a.docstatus = 1 and r.purpose = 'Employee Salary' and a.fiscal_year = \'""" + str(filters.fiscal_year) + "\'"

# 	salary = """select 
# 		CONVERT(a.month, UNSIGNED) as month, 
# 		a.gross_pay, 
# 		a.fiscal_year as fyear,
# 		(select b.amount from `tabSalary Detail` b where b.salary_component = 'Basic Pay' and b.parent = a.name) as basic_pay,
# 		(select b.amount from `tabSalary Detail` b where b.salary_component = 'Salary Tax' and b.parent = a.name) as tds,
# 		(select b.amount from `tabSalary Detail` b where b.salary_component = 'PF' and b.parent = a.name) as nppf,
# 		ifnull((select b.amount from `tabSalary Detail` b where b.salary_component = 'Group Insurance Scheme' and b.parent = a.name),0) as gis,
# 		(select b.amount from `tabSalary Detail` b where b.salary_component = 'Communication Allowance' and b.parent = a.name) as comm_all,
# 		(select b.amount from `tabSalary Detail` b where b.salary_component = 'Health Contribution' and b.parent = a.name) as health,
# 		r.receipt_number,
# 		DATE_FORMAT(r.receipt_date, '%Y-%m-%d') AS receipt_date
# 	from `tabSalary Slip` a
# 	JOIN `tabTDS Receipt Entry` r
# 		ON a.fiscal_year = r.fiscal_year
# 		AND a.month = r.month
# 		AND a.docstatus = 1
# 		AND r.purpose = 'Employee Salary'
# 		AND a.fiscal_year = '{fyear}'
# 		{receipt_cond}
# 	""".format(
# 		fyear=filters.fiscal_year,
# 		receipt_cond=receipt_cond
# 	)

# 	if filters.employee:
# 		salary = salary + " AND a.employee = \'" + str(filters.employee) + "\'"

# 	receipt_cond = ""
# 	if filters.get("receipt_date"):
# 		receipt_cond = " AND r.receipt_date = '{0}'".format(filters.receipt_date)	

# 	salary+=" order by r.receipt_date asc;"

# 	# frappe.throw(salary)
# 	datas = frappe.db.sql(salary, as_dict=True)
# 	for d in datas:
# 		#frappe.msgprint(str(d.nppf))
# 		row = [get_month(d.month)+"-"+d.fyear, 
# 			  "Salary", 
# 			  d.basic_pay, 
# 			  round(flt(d.gross_pay) - flt(d.basic_pay) - (flt(d.comm_all) / 2), 2), 
# 			  round(flt(d.gross_pay)-(flt(d.comm_all) / 2),2), 
# 			  d.nppf,
# 			  d.gis,
# 			  flt(d.nppf)+flt(d.gis), 
# 			  flt(d.gross_pay) - flt(d.nppf) - flt(d.gis) - (flt(d.comm_all) / 2), 
# 			  d.tds if d.tds else 0, 
# 			  d.health,
# 			  d.receipt_number, 
# 			  d.receipt_date,
# 			  ""]
# 		data.append(row)
# 	#Leave Encashment 
# 	if filters.employee:
# 		fiscal_year = frappe.db.sql("select name, year_start_date, year_end_date from `tabFiscal Year` where name='{}' and disabled = 0".format(filters.fiscal_year), as_dict=True)
# 		if not fiscal_year:
# 			frappe.throw(_("missing value for <b>Fiscal Year</b> {} OR it is disabled").format(filters.fiscal_year), title="Fiscal Year missing")

# 		# encash_data = frappe.db.sql("select a.encashment_date AS date, a.encashment_amount, a.encashment_tax, r.receipt_number, r.receipt_date from `tabLeave Encashment` a, `tabRRCO Receipt Entries` r where a.name = r.purchase_invoice and a.employee = %s and a.docstatus = 1 and a.encashment_date between \'" + filters.fiscal_year + "-01-01\' and \'" + filters.fiscal_year + "-12-31\'", filters.employee, as_dict=True) 
# 		# encash_data = frappe.db.sql("select a.encashment_date, MONTH(a.encashment_date) AS month, YEAR(a.encashment_date) AS year, a.encashment_amount, a.encashment_tax, r.receipt_number, r.receipt_date from `tabLeave Encashment` a, `tabRRCO Receipt Entries` r where a.name = r.purchase_invoice and a.employee = %s and a.docstatus = 1 and a.encashment_date between \'" + filters.fiscal_year + "-01-01\' and \'" + filters.fiscal_year + "-12-31\'", filters.employee, as_dict=True) 
# 		encash_data = frappe.db.sql("""SELECT 
# 					DATE_FORMAT(a.encashment_date, '%d-%m-%Y') AS encashment_date,
# 						r.receipt_number, 
# 						MONTH(a.encashment_date) AS month, YEAR(a.encashment_date) AS year, 
# 						a.encashment_amount, a.encashment_tax, 
# 						r.receipt_number, 
# 						DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
# 					from `tabLeave Encashment` a LEFT JOIN `tabTDS Receipt Entry` r
# 						ON a.name = r.invoice_no
# 					WHERE a.employee = '"""+filters.employee+"""' and a.docstatus = 1 
# 						and a.encashment_date between '"""+ str(fiscal_year[0]["year_start_date"]) + """' and '""" + str(fiscal_year[0]["year_end_date"]) + """ ' """, as_dict=True) 
# 		# frappe.msgprint(str(encash_data))
# 		if encash_data:
# 			for a in encash_data:
# 				row = [
# 				# str(a.date)[5:7], 
# 				get_month(a.month)+"-"+str(a.year),
# 				"Leave Encashment", 
# 				0,
# 				0, 
# 				a.encashment_amount, 
# 				0, 
# 				0, 
# 				0, 
# 				a.encashment_amount, 
# 				a.encashment_tax if a.encashment_tax else 0, 
# 				0, 
# 				a.receipt_number, 
# 				a.receipt_date,
# 				a.encashment_date]
# 			data.append(row)

# 		# night_shift = frappe.db.sql("""select 
# 		# 					DATE_FORMAT(a.posting_date, '%d-%m-%Y') AS shift_date,
# 		# 					b.rate, 
# 		# 					b.amount,
# 		# 					b.no_of_shifts, 
# 		# 					b.shift_tax,
# 		# 					MONTH(a.posting_date) AS month, 
# 		# 					YEAR(a.posting_date) AS year	
# 		# 				from `tabProcess Shift Payment` a, `tabShift Payment Details` b 
# 		# 				where a.name = b.parent
# 		# 				and a.docstatus = 1
# 		# 				and a.posting_date between '"""+ filters.fiscal_year + """-01-01' and '""" + filters.fiscal_year + """-12-31'""", as_dict=True)
# 		# if night_shift:
# 		# 	for a in night_shift:
# 		# 		row = [
# 		# 		# str(a.date)[5:7], 
# 		# 		get_month(a.month)+"-"+str(a.year),
# 		# 		"Night Shift", 
# 		# 		0,
# 		# 		0, 
# 		# 		a.amount, 
# 		# 		0, 
# 		# 		0, 
# 		# 		0, 
# 		# 		a.amount, 
# 		# 		a.shift_tax if a.shift_tax else 0,
# 		# 		0, 
# 		# 		"", 
# 		# 		"",
# 		# 		a.shift_date]
# 		# 	data.append(row)
# 		# Overtime
# 		# overtime_data = frappe.db.sql("""select 
# 		# 			DATE_FORMAT(a.posting_date, '%d-%m-%Y') AS overtime_date,
# 		# 			r.receipt_number, 
# 		# 			MONTH(a.posting_date) AS month, YEAR(a.posting_date) AS year,
# 		# 			a.total_amount as overtime_amt, a.overtime_tax, 
# 		# 			r.receipt_number,
# 		# 			DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
# 		# 			from `tabOvertime Application` a, `tabRRCO Receipt Entries` r where a.name = r.purchase_invoice 
# 		# 			and a.employee = """+filters.employee+""" and a.docstatus = 1 
# 		# 			and a.posting_date between '"""	+ filters.fiscal_year + """-01-01' and '""" + filters.fiscal_year + """-12-31'""", as_dict=True)
# 		# overtime_data = frappe.db.sql("""select 
# 		# 			DATE_FORMAT(a.posting_date, '%d-%m-%Y') AS overtime_date,
# 		# 			r.receipt_number, 
# 		# 			MONTH(a.posting_date) AS month, YEAR(a.posting_date) AS year,
# 		# 			a.total_amount as overtime_amt, a.overtime_tax, 
# 		# 			r.receipt_number,
# 		# 			DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
# 		# 			from `tabOvertime Application` a LEFT JOIN `tabTDS Receipt Entry` r 
# 		# 			ON a.name = r.invoice_no
# 		# 			where a.employee = """+filters.employee+""" and a.docstatus = 1 
# 		# 			and a.posting_date between '"""	+ filters.fiscal_year + """-01-01' and '""" + filters.fiscal_year + """-12-31'""", as_dict=True)
# 		# if overtime_data:
# 		# 	for a in overtime_data:
# 		# 		row = [
# 		# 		# str(a.date)[5:7], 
# 		# 		get_month(a.month)+"-"+str(a.year),
# 		# 		"Overtime", 
# 		# 		0,
# 		# 		0, 
# 		# 		a.overtime_amt, 
# 		# 		0, 
# 		# 		0, 
# 		# 		0, 
# 		# 		a.overtime_amt, 
# 		# 		a.overtime_tax if a.overtime_tax else 0,
# 		# 		0, 
# 		# 		a.receipt_number, 
# 		# 		a.receipt_date,
# 		# 		a.overtime_date]
# 		# 	data.append(row)

# 		#Bonus
# 		bonus = frappe.db.sql("""
# 					select b.name, b.fiscal_year AS fyear,
# 					r.receipt_number, DATE_FORMAT(b.posting_date, '%d-%m-%Y') AS posting_date,
# 					MONTH(b.posting_date) AS month, 
# 					r.receipt_number, 
# 					DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
# 					from tabBonus b, `tabTDS Receipt Entry` r
# 					where b.fiscal_year = r.fiscal_year 
# 					and b.docstatus = 1 
# 					and b.posting_date between "{from_date}" and "{to_date}" 
# 					and r.purpose = 'Bonus' 
# 				""".format(from_date = str(filters.fiscal_year) + "-01-01",
# 					  to_date = str(filters.fiscal_year) + "-12-31"), as_dict=1)
# 		for b in bonus:
# 			amt = frappe.db.sql("""
# 				     	select amount, tax_amount, balance_amount  
# 					from `tabBonus Details` 
# 					where parent = %s and employee = %s
# 				      """, (b.name, filters.employee), as_dict=1)
# 			for a in amt:
# 				row = [
# 				get_month(b.month)+"-"+str(b.fyear),
# 				"Bonus", 
# 				0, 
# 				0, 
# 				a.amount, 
# 				0, 
# 				0, 
# 				0, 
# 				a.amount, 
# 				a.tax_amount if a.tax_amount else 0,
# 				0, 
# 				b.receipt_number, 
# 				b.receipt_date,
# 				b.posting_date]	
# 			data.append(row)
# 		#PVBA
# 		# pbva = frappe.db.sql("""
# 		# 			select b.name, b.fiscal_year  as year, b.posting_date, MONTH(b.posting_date) as month, r.receipt_number, r.receipt_date 
# 		# 			from tabPBVA b, `tabRRCO Receipt Entries` r
# 		# 			where b.fiscal_year+1 = r.fiscal_year and b.docstatus = 1 and b.posting_date between %s and %s and r.purpose = 'PBVA' 
# 		# 		      """, (str(filters.fiscal_year) + "-01-01", str(filters.fiscal_year) + "-12-31"), as_dict=1)
# 		pbva = frappe.db.sql("""
# 					select b.name, b.fiscal_year  as year, r.pbva,
# 					DATE_FORMAT(b.posting_date, '%d-%m-%Y') AS posting_date,
# 					MONTH(b.posting_date) as month, 
# 					r.receipt_number, 
# 					DATE_FORMAT(r.receipt_date, '%d-%m-%Y') AS receipt_date
# 					from tabPBVA b, `tabTDS Receipt Entry` r
# 					where b.fiscal_year = r.fiscal_year 
# 					and b.docstatus = 1 
# 					and b.posting_date between "{fdate}" and "{tdate}" 
# 					and r.purpose = 'PBVA' 
# 					and b.name = r.pbva
# 				      """.format(fdate= str(filters.fiscal_year) + "-01-01", tdate = str(filters.fiscal_year) + "-12-31"), as_dict=1)
# 		for b in pbva:
# 			amt = frappe.db.sql("""
# 				     	select amount, tax_amount, balance_amount  
# 					from `tabPBVA Details` 
# 					where parent = %s and employee = %s
# 				      """, (b.name, filters.employee), as_dict=1)
# 			for a in amt:
# 				row = [get_month(b.month)+"-"+str(b.year), 
# 					  "PBVA", 
# 					  0, 
# 					  0, 
# 					  a.amount, 
# 					  0, 
# 					  0, 
# 					  0, 
# 					  a.amount, 
# 					  a.tax_amount if a.tax_amount else 0, 
# 					  0, 
# 					  b.receipt_number, 
# 					  b.receipt_date,
# 					  b.posting_date]	
# 				data.append(row)
# 	# frappe.throw('{}'.format(data))
# 	return data

# def validate_filters(filters):
# 	if not filters.fiscal_year:
# 		frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))
# 	start, end = frappe.db.get_value("Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"])
# 	filters.year_start = start
# 	filters.year_end = end

# def get_columns():
# 	return [
# 		{
# 		  "fieldname": "month-fyear",
# 		  "label": "Month-Year",
# 		  "fieldtype": "Data",
# 		  "width": 100
# 		},
# 		{
# 		  "fieldname": "type",
# 		  "label": "Income Type",
# 		  "fieldtype": "Data",
# 		  "width": 100
# 		},
# 		{
# 		  "fieldname": "basic",
# 		  "label": "Basic Salary",
# 		  "fieldtype": "Currency",
# 		  "width": 150
# 		},
# 		{
# 		  "fieldname": "others",
# 		  "label": "Allowances",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "total",
# 		  "label": "Total Income",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "pf",
# 		  "label": "PF",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "gis",
# 		  "label": "GIS",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "totalPfGis",
# 		  "label": "Total of PF & GIS",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "taxable",
# 		  "label": "Taxable Income",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "tds",
# 		  "label": "TDS Amount",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "health",
# 		  "label": "Health",
# 		  "fieldtype": "Currency",
# 		  "width": 120
# 		},
# 		{
# 		  "fieldname": "receipt_number",
# 		  "label": "RRCO Receipt No.",
# 		  "fieldtype": "Data",
# 		  "width": 150
# 		},
# 		{
# 		  "fieldname": "receipt_date",
# 		  "label": "RRCO Receipt Date",
# 		  "fieldtype": "Date",
# 		  "width": 130
# 		},
# 		{
# 		  "fieldname": "post_date",
# 		  "label": "Posting Date",
# 		  "fieldtype": "Data",
# 		  "width": 100
# 		},
# 	]

# def get_month(month):
# 	if month == 1:
# 		return "Jan"
# 	elif month == 2:
# 		return "Feb"
# 	elif month == 3:
# 		return "Mar"
# 	elif month == 4:
# 		return "Apr"
# 	elif month == 5:
# 		return "May"
# 	elif month == 6:
# 		return "Jun"
# 	elif month == 7:
# 		return "Jul"
# 	elif month == 8:
# 		return "Aug"
# 	elif month == 9:
# 		return "Sep"
# 	elif month == 10:
# 		return "Oct"
# 	elif month == 11:
# 		return "Nov"
# 	elif month == 12:
# 		return "Dec"
# 	else:
# 		return "None"