// Copyright (c) 2025, Frappe Technologies Pvt. Ltd.
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Salary Advance Report"] = {
	"filters": [
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": "150px"
		}
	]
};
