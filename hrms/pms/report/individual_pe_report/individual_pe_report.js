// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Individual PE Report"] = {
	"filters": [
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.sys_defaults.fiscal_year,
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"on_change": function(query_report) {
				var emp = query_report.get_values().employee;
				if (!emp) {
					frappe.query_report.set_filter_value("e_name", null);
					frappe.query_report.set_filter_value("designation", null);
					frappe.query_report.set_filter_value("branch", null);
					return;
				}
				frappe.model.with_doc("Employee", emp, function(r) {
					var fy = frappe.model.get_doc("Employee", emp);
					frappe.query_report.set_filter_value("e_name", fy.employee_name);
					frappe.query_report.set_filter_value("designation", fy.designation);
					frappe.query_report.set_filter_value("branch", fy.branch);
					// frappe.query_report.set_filter_value("cid", fy.passport_number);
					// frappe.query_report.set_filter_value("tpn", fy.tpn_number);
					frappe.query_report.refresh();
				});
			}
		},
		{
			"fieldname":"e_name",
			"fieldtype":"Data",
			"label": __("Employee Name"),
			"read_only": 1
		},
		{
			"fieldname":"designation",
			"fieldtype":"Link",
			"label": __("Designation"),
			"options": "Designation",
			"read_only": 1
		},
		{
			"fieldname":"branch",
			"fieldtype":"Link",
			"label": __("Branch"),
			"options": "Branch",
			"read_only": 1
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": "100px",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"overall",
			"fieldtype":"Check",
			"label": __("Show Overall PE Report"),
			"default": 0,
		},
	]
};
