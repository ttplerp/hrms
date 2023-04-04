// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["LTC Process Report"] = {
	"filters": [
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.sys_defaults.fiscal_year,
		},
		{
			"fieldname": "uinput",
			"label": ("Options"),
			"fieldtype": "Select",
			"width": "80",
			"options": ["LTC", "PBVA", "Bonus"],
			"reqd": 1,
			"default":"LTC"
		}
	]
};
