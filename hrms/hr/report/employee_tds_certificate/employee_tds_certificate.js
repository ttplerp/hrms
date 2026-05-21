
frappe.query_reports["Employee TDS Certificate"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: "From Date",
			fieldtype: "Date",
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: "To Date",
			fieldtype: "Date",
			reqd: 1
		},
		{
			fieldname: "employee",
			label: "Employee",
			fieldtype: "Link",
			options: "Employee",
			reqd: 1,
			on_change: function (query_report) {
				let emp = query_report.get_values().employee;
				if (!emp) return;

				frappe.db.get_doc("Employee", emp).then(d => {
					frappe.query_report.set_filter_value("e_name", d.employee_name);
					frappe.query_report.set_filter_value("cid", d.passport_number);
					frappe.query_report.set_filter_value("tpn", d.tpn_number);
				});
			}
		},
		{
			fieldname: "e_name",
			label: "Employee Name",
			fieldtype: "Data",
			read_only: 1
		},
		{
			fieldname: "cid",
			label: "CID",
			fieldtype: "Data",
			read_only: 1
		},
		{
			fieldname: "tpn",
			label: "TPN",
			fieldtype: "Data",
			read_only: 1
		}
	]
};




// // Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// // License: GNU General Public License v3. See license.txt

// frappe.query_reports["Employee TDS Certificate"] = {
// 	"filters": [
// 		// {
// 		// 	"fieldname":"fiscal_year",
// 		// 	"label": __("Fiscal Year"),
// 		// 	"fieldtype": "Link",
// 		// 	"options": "Fiscal Year",
// 		// 	"default": frappe.defaults.get_user_default("fiscal_year"),
// 		// },
// 		// {
// 		// 	"fieldname":"receipt_date",
// 		// 	"label": __("Receipt Date"),
// 		// 	"fieldtype": "Date",
// 		// },
// 		{
// 			fieldname: "from_date",
// 			label: "From Date",
// 			fieldtype: "Date",
// 			reqd: 1
// 		},
// 		{
// 			fieldname: "to_date",
// 			label: "To Date",
// 			fieldtype: "Date",
// 			reqd: 1
// 		},
// 		{
// 			"fieldname":"employee",
// 			"label": __("Employee"),
// 			"fieldtype": "Link",
// 			"options": "Employee",
// 			"reqd": 1,
// 			"on_change": function(query_report) {
// 				var emp = query_report.get_values().employee;
// 				if (!emp) {
// 					frappe.query_report.set_filter_value("e_name", "");
// 					frappe.query_report.set_filter_value("cid", "");
// 					frappe.query_report.set_filter_value("tpn", "");
// 					frappe.query_report.refresh();
// 					return;
// 				}
// 				frappe.model.with_doc("Employee", emp, function(r) {
// 					var fy = frappe.model.get_doc("Employee", emp);
// 					frappe.query_report.set_filter_value("e_name", fy.employee_name);
// 					frappe.query_report.set_filter_value("cid", fy.passport_number);
// 					frappe.query_report.set_filter_value("tpn", fy.tpn_number);
// 					frappe.query_report.refresh();
// 				});
// 			}
// 		},
// 		{
// 			"fieldname":"e_name",
// 			"fieldtype":"Data",
// 			"label": __("Employee Name"),
// 			"read_only": 1
// 		},
// 		{
// 			"fieldname":"cid",
// 			"fieldtype":"Data",
// 			"label": __("CID"),
// 			"read_only": 1
// 		},
// 		{
// 			"fieldname":"tpn",
// 			"fieldtype":"Data",
// 			"label": __("TPN"),
// 			"read_only": 1
// 		},
// 		{
// 			"fieldname":"approver",
// 			"label":"Approver",
// 			"fieldtype": "Link",
// 			"options": "Employee",
// 			"on_change": function(query_report) {
// 				var emp = query_report.get_values().approver;
// 				if (!emp) {
// 					return;
// 				}
// 				frappe.model.with_doc("Employee", emp, function(r) {
// 					var fy = frappe.model.get_doc("Employee", emp);
// 					frappe.query_report.set_filter_value("approver_name", fy.employee_name);
// 					frappe.query_report.set_filter_value("approver_designation", fy.designation);
// 					frappe.query_report.refresh();
// 				});
// 			}
// 		},
// 		{
// 			"fieldname":"approver_name",
// 			"label":"Approver Name",
// 			"fieldtype": "Data",
// 			"read_only": 1

// 		},
// 		{
// 			"fieldname":"approver_designation",
// 			"label":"Approver Designation",
// 			"fieldtype": "Data",
// 			"read_only": 1
// 		}
// 	]
// }
