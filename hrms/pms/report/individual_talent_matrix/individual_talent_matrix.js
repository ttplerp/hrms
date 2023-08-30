// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Individual Talent Matrix"] = {
	"filters": [
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.sys_defaults.fiscal_year,
		},
		{
			fieldname: "potential",
			label: __("Potential"),
			fieldtype: "Select",
			options: [
				{ "value": "Weekly", "label": __("High Potentail") },
				{ "value": "Monthly", "label": __("Moderate Potential") },
				{ "value": "Quarterly", "label": __("Low Potentail") },
			],
			default: "High Potentail",
			reqd: 1
		},
		{
			fieldname: "performance",
			label: __("Performance"),
			fieldtype: "Select",
			options: [
				{ "value": "Weekly", "label": __("High Performance") },
				{ "value": "Monthly", "label": __("Moderate Performance") },
				{ "value": "Quarterly", "label": __("Low Performance") },
			],
			default: "High Performance",
			reqd: 1
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": "120px",
			"default": frappe.defaults.get_user_default("Company")
		},
	]
};
