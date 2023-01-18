// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Dispatch Report"] = {
	"filters": [
		{
			"fieldname": "dispatch_type",
			"label": "Dispatch Type",
			"fieldtype": "Select",
			"options": ["Incoming", "Out-Going"],
			"reqd": 1,
			on_change: function(query_report) {
				var d_type = query_report.get_filter_value('dispatch_type');
				if (d_type == 'Incoming'){
					query_report.get_filter('purpose').toggle(d_type == 'Incoming' ? 0:1);
				} else {
					query_report.get_filter('purpose').toggle(d_type == 'Out-Going' ? 1:0);
				}
				query_report.refresh("purpose");
			}
		},
		{
			"fieldname": "purpose",
			"label": "Purpose",
			"fieldtype": "Select",
			"options": ["", "Studies", "Employment", "Training", "Scholarship", "Marriage Certificate"],
			"reqd": 0,
			"hidden": 1
		}
	]
};
