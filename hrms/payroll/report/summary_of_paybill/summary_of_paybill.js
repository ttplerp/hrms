// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Summary of Paybill"] = {
	"filters": [
		{
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "reqd": 0
        },
        {
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "All\nActive\nInactive",
			"default": "Active"
		},
	]
};
