// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Employee Advance Report"] = {
	"filters": [
		{
			"fieldname": "employee",
			"label": ("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
		},
		{
			"fieldname": "advance_type",
			"label": __("Advance Type"),
			"fieldtype": "Select",
			"options": "\nSalary Advance\nImprest Advance\nEmployee Loan",
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_start_date"),
			"reqd": 1,
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_end_date"),
			"reqd": 1,
		},
	]
};
