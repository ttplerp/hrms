// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Daily Activity Log Report"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"employee",
			"label": __("Select Employee"),
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname":"branch",
			"label": __("Select Branch"),
			"fieldtype": "Link",
			"options": "Branch"
		},
		{
			"fieldname":"department",
			"label": __("Select Department"),
			"fieldtype": "Link",
			"options": "Department"
		},
		{
			"fieldname":"section",
			"label": __("Select Section"),
			"fieldtype": "Link",
			"options": "Department"
		},
		{
			"fieldname":"unit",
			"label": __("Select Unit"),
			"fieldtype": "Link",
			"options": "Department"
		}
	]
};
