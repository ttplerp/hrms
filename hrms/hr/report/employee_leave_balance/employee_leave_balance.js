// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Employee Leave Balance"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			//"reqd": 1,
			//"default": frappe.defaults.get_default("year_start_date")
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			//"reqd": 1,
			//"default": frappe.defaults.get_default("year_end_date")
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"get_query": function () {
				return {
					filters: {
						"is_department": 1
					}
				};
			},
		},
		{
			"fieldname": "division",
			"label": __("Division"),
			"fieldtype": "Link",
			"options": "Department",
			"get_query": function () {
				return {
					filters: {
						"is_division": 1
					}
				};
			},
		},
		{
			"fieldname": "section",
			"label": __("Section"),
			"fieldtype": "Link",
			"options": "Department",
			"get_query": function () {
				return {
					filters: {
						"is_section": 1
					}
				};
			},
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			//"reqd": 1,
			//"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "employee_status",
			"label": __("Employee Status"),
			"fieldtype": "Select",
			"options": [
				"",
				{ "value": "Active", "label": __("Active") },
				{ "value": "Inactive", "label": __("Inactive") },
				{ "value": "Suspended", "label": __("Suspended") },
				{ "value": "Left", "label": __("Left") },
			],
			"default": "Active",
		}
	],

	// onload: () => {
	// 	frappe.call({
	// 		type: "GET",
	// 		method: "hrms.hr.utils.get_leave_period",
	// 		args: {
	// 			"from_date": frappe.defaults.get_default("year_start_date"),
	// 			"to_date": frappe.defaults.get_default("year_end_date"),
	// 			"company": frappe.defaults.get_user_default("Company")
	// 		},
	// 		freeze: true,
	// 		callback: (data) => {
	// 			console.log(frappe)
	// 			frappe.query_report.set_filter_value("from_date", data.message[0].from_date);
	// 			frappe.query_report.set_filter_value("to_date", data.message[0].to_date);
	// 		}
	// 	});
	// }
}
