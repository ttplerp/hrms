frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Employee Leave Balance"] = {
	method: "hrms.hr.dashboard_chart_source.employee_leave_balance.employee_leave_balance.get_data",
	// filters: [
	// 	{
	// 		fieldname: "company",
	// 		label: __("Company"),
	// 		fieldtype: "Link",
	// 		options: "Company",
	// 		default: frappe.defaults.get_user_default("Company")
	// 	},
	// ]
};