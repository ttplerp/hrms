// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Employee TDS Certificate"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("company"),
			"reqd": 1,
		},
		{
			"fieldname":"fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"reqd": 1,
		},
		{
			"fieldname":"employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"reqd": 1,
			"on_change": function(query_report) {
				var emp = query_report.get_values().employee;
				if (!emp) {
					return;
				}
				frappe.model.with_doc("Employee", emp, function(r) {
					var fy = frappe.model.get_doc("Employee", emp);
					frappe.query_report.set_filter_value("e_name", fy.employee_name);
					frappe.query_report.set_filter_value("cid", fy.cid_no);
					frappe.query_report.set_filter_value("tpn", fy.tpn_number);
					frappe.query_report.refresh();
				});

				var com = query_report.get_values().company;
				if (!com) {
					return;
				}
				frappe.model.with_doc("Company", com, function(r) {
					var c = frappe.model.get_doc("Company", com);
					frappe.query_report.set_filter_value("seal", c.seal);
					frappe.query_report.set_filter_value("signature", c.signature);
					frappe.query_report.set_filter_value("authorizer_name", c.authorizer_name);
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
			"fieldname":"cid",
			"fieldtype":"Data",
			"label": __("CID"),
			"read_only": 1
		},
		{
			"fieldname":"tpn",
			"fieldtype":"Data",
			"label": __("TPN"),
			"read_only": 1
		},
		
		{
			"fieldname":"signature",
			"label":"Signature",
			"fieldtype": "Data",
			"read_only": 1,
			"hidden": 1
		},
		{
			"fieldname":"seal",
			"label":"Seal",
			"fieldtype": "Data",
			"read_only": 1,
			"hidden": 1
		},
		{
			"fieldname":"authorizer_name",
			"label":"Authorizer Name",
			"fieldtype": "Data",
			"read_only": 1,
			"hidden": 1
		},
	]
}
