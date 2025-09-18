// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["SWS Loan Report"] = {
	"filters": [
		{
			"fieldname": "fiscal_yaer",
			"label": __("Fiscal Year"),
			"fieldtype": "Date",
			"width": "150px"
		},
		{
			"fieldname": "yearmonth",
			"label": __("Month"),
			"fieldtype": "Date",
			"width": "150px"
		},

		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": "150px"
		}
	]
};
