# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
'''
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
1.0		  SSK		                   03/08/2016         Taking care of Duplication of columns
--------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _

def execute(filters=None):
	if not filters: 
		filters = {}
	data    = []
	columns = []
		
	data = get_data(filters)
	if not data:
				return columns, data
		
	columns = get_columns(data)
	
	return columns, data
	
def get_columns(data):
	columns = [
		_("Employee") + ":Link/Employee:80", _("Employee Name") + "::140", _("Designation") + ":Link/Designation:120",
				_("CID") + "::120",_("PF Tier") + "::100", _("Basic Pay") + ":Currency:120",_("PF Account#") + "::120",
				_("Employee PF") + ":Currency:120", _("Employer PF") + ":Currency:120", _("Total") + ":Currency:120",
				_("Company") + ":Link/Branch:120", _("Cost Center") + ":Link/Cost Center:120", _("Branch") + ":Link/Branch:120", _("Department") + ":Link/Department:120",
				_("Division") + ":Link/Division:120", _("Section") + ":Link/Section:120", _("Year") + "::80", _("Month") + "::80", _("Pay Roll Entry ID") + ":Link/Payroll Entry:100"
	]
	
	return columns
	
def get_data(filters):
	conditions, filters = get_conditions(filters)
	 
	data = frappe.db.sql("""
			SELECT t1.employee, t3.employee_name, t1.designation, t3.passport_number, t3.pf_tiers,
				SUM(CASE WHEN t2.salary_component = 'Basic Pay' THEN IFNULL(t2.amount, 0) ELSE 0 END) AS basicpay,
				t3.pf_number,
				SUM(CASE WHEN t2.salary_component = 'PF' THEN IFNULL(t2.amount, 0) ELSE 0 END) AS employeepf,
				SUM(CASE WHEN t2.salary_component = 'PF' THEN IFNULL(t2.amount, 0) ELSE 0 END) AS employerpf,
				SUM(CASE WHEN t2.salary_component = 'PF' THEN IFNULL(t2.amount, 0) * 2 ELSE 0 END) AS total,
				t1.company, t1.branch, t1.cost_center, t1.department, t1.division, t1.section,
				t1.fiscal_year, t1.month, t1.payroll_entry AS payroll_entry_id
			FROM `tabSalary Slip` t1
			JOIN `tabSalary Detail` t2 ON t2.parent = t1.name
			JOIN `tabEmployee` t3 ON t3.employee = t1.employee
			WHERE t1.docstatus = 1 %s
			AND t2.salary_component IN ('Basic Pay', 'PF')
			GROUP BY t1.employee, t3.employee_name, t1.designation, t3.passport_number, t3.pf_number,
				t1.company, t1.branch, t1.cost_center, t1.department, t1.division, t1.section,
				t1.fiscal_year, t1.month, t1.payroll_entry
		""" % conditions, filters)

	return data	
 

	
def get_conditions(filters):
	conditions = ""
	if filters.get("month"):
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
			"Dec"].index(filters["month"]) + 1
		filters["month"] = month
		conditions += " and t1.month = %(month)s"
	
	if filters.get("fiscal_year"): conditions += " and t1.fiscal_year = %(fiscal_year)s"
	if filters.get("company"): conditions += " and t1.company = %(company)s"
	if filters.get("employee"): conditions += " and t1.employee = %(employee)s"
	if filters.get("tier"): conditions += " and t3.pf_tiers = %(tier)s"
	if filters.get("cost_center"): conditions += " and exists(select 1 from `tabCost Center` cc where t1.cost_center = cc.name and (cc.parent_cost_center = '{0}' or cc.name = '{0}'))".format(filters.cost_center)
	return conditions, filters
	
