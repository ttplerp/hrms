// Copyright (c) 2025, Frappe Technologies Pvt. Ltd.
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Salary Advance Report"] = {
	"filters": [
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options":"Fiscal Year",
			"width": "150px"
		},
		{
            "fieldname": "month",
            "label": __("Month"),
            "fieldtype": "Select",
            "options": "\nJAN\nFEB\nMAR\nAPR\nMAY\nJUN\nJUL\nAUG\nSEP\nOCT\nNOV\nDEC",
            "width": "120px"
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
