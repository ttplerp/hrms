// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Employee Checkin Report"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"employee",
			"label": __("Select Employee"),
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname":"division",
			"label": __("Select Division"),
			"fieldtype": "Link",
			"options": "Department",
			"get_query": function() {return {'filters': [['Department', 'is_division', '=', '1']]}},
			on_change: function() {
				frappe.query_report.set_filter_value('section', "");
			},
		},
		{
			"fieldname":"section",
			"label": __("Select Section"),
			"fieldtype": "Link",
			"options": "Department",
			"get_query": function(txn) {
				return {
					'filters': [
						['Department', 'is_section', '=', '1'],
						['parent_department', '=', frappe.query_report.get_filter_value("division")]
					]
				}
			}
		},
		{
			"fieldname":"unit",
			"label": __("Select Unit"),
			"fieldtype": "Link",
			"options": "Department",
			"get_query": function(txn) {
				return {
					'filters': [
						['Department', 'is_unit', '=', '1']
					]
				}
			}
		}
	]
};
