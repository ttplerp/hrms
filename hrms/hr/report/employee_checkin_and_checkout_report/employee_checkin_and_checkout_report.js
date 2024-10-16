// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Employee Checkin and Checkout Report"] = {
	"filters": [
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"reqd":0,
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd":1,
			"read_only": 0,
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd":1,
			"read_only": 0,
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname": "shift_type",
			"label": __("Shift Type"),
			"fieldtype": "Link",
			"options": "Shift Type",
		},
		{
			"fieldname": "late_checkin_out",
			"label": __("Late CheckIn or EarlyExit"),
			"fieldtype": "Check",
			"options": "",
			"default": 0,
		},
		{
			"fieldname": "have_not_checkin",
			"label": __("Have Not Checkin"),
			"fieldtype": "Check",
			"options": "",
			"default": 0,
			// "on_change": function(query_report) {
			// 	var have_not_checkin = query_report.get_values().have_not_checkin;
			// 	if (have_not_checkin) {
			// 		var late_checkin_out = frappe.query_report.get_filter_value('late_checkin_out');
			// 		if (late_checkin_out) {
			// 			console.log(late_checkin_out)
			// 			query_report.filters_by_name.late_checkin_out.set_input(0);
			// 			query_report.trigger_refresh();
			// 		}
			// 	}
			// },
		},
	]
};
