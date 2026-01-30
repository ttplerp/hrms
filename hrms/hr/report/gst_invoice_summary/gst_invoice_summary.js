// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GST Invoice Summary"] = {
	"filters": [
		{
			"fieldname": "service_type",
			"label": __("Service Type"),
			"fieldtype": "Link",
			"options": "GST Service Type",
			"width": "80",
			"default": ""
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "response_status",
			"label": __("Response Status"),
			"fieldtype": "Select",
			"options": "\nSUCCESS\nFAILURE\nNot Required",
			"width": "80",
			"default": ""
		},
		{
			"fieldname": "customer_tpn",
			"label": __("Customer TPN"),
			"fieldtype": "Data",
			"width": "80",
			"default": ""
		}
	]
};
