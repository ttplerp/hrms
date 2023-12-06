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
			"fieldname": "from_month",
			"label": __("From"),
			"fieldtype": "Select",
			"options": "\nJan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
			"default": "Jan",
			// "default": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()],
		},
		{
			"fieldname": "to_month",
			"label": __("To"),
			"fieldtype": "Select",
			"options": "\nJan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
			"default": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()],
		},
		{
			"fieldname": "pot_per",
			"label": __("Select"),
			"fieldtype": "Select",
			"options": "\nFuture Senior Leader\nGrowth Employee\nHigh-Impact Performer\nTrusted Professional\nUnrealized Performer\nCore Employee\nEffective Employee\nInconsistent Performer\nLow Performer",
			"default": "Core Employee"
		},
		{
			"fieldname":"exclude_muster_roll",
			"fieldtype":"Check",
			"label": __("Exclude Muster Roll"),
			"default": 0,
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
