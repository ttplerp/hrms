// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["MR Monthly Overtime Register"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": "Jan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
			"default": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()],
		},
		{
			"fieldname": "year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"reqd": 1
	    },
		{
			"fieldname": "employee_type",
			"label": __("Employee Type"),
			"fieldtype": "Select",
			"options": ['Muster Roll Employee'],
			"reqd": 1
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
			"default":"",
			"get_query": function() {
				return {
					'filters': [
						['Cost Center', 'disabled', '!=', '1'],
						['Cost Center', 'is_group', '!=', '1']
					]
				};
			}
		}
	],

	// "onload": function(me) {
	// 	return frappe.call({
	// 		method: "erpnext.projects.report.mr_monthly_overtime_register.mr_monthly_overtime_register.get_years",
	// 		callback: function(r) {
	// 			if (r.message && Array.isArray(r.message)) {
	// 				var year_filter = me.filters_by_name.year;
					
	// 				// Verify that the year_filter exists
	// 				if (year_filter) {
	// 					// Set dropdown options as newline-separated string of years
	// 					year_filter.df.options = r.message.join("\n");
						
	// 					// Set the default year to the first year in the response
	// 					year_filter.df.default = r.message[0];

	// 					// Refresh and set input after setting options and default
	// 					year_filter.refresh();
	// 					year_filter.set_input(year_filter.df.default);
	// 				} else {
	// 					console.error("Year filter not found.");
	// 				}
	// 			} else {
	// 				console.error("Invalid response format:", r);
	// 			}
	// 		}
	// 	});
	// }
	"onload": function (me) {
			return frappe.call({
					method: "hrms.hr.report.mr_monthly_overtime_register.mr_monthly_overtime_register.get_years",
					callback: function (r) {
							var year_filter = me.filters_by_name.year;
							year_filter.df.options = r.message;
							year_filter.df.default = r.message.split("\n")[0];
							year_filter.refresh();
							year_filter.set_input(year_filter.df.default);
					}
			});
	}
};
