// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Training Event', {
	onload_post_render: function (frm) {
		frm.get_field("employees").grid.set_multiple_add("employee");
	},
	refresh: function (frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Training Result"), function () {
				frappe.route_options = {
					training_event: frm.doc.name
				};
				frappe.set_route("List", "Training Result");
			});
			frm.add_custom_button(__("Training Feedback"), function () {
				frappe.route_options = {
					training_event: frm.doc.name
				};
				frappe.set_route("List", "Training Feedback");
			});
		}
		frm.events.set_employee_query(frm);
	},

	set_employee_query: function(frm) {
		let emp = [];
		for (let d in frm.doc.employees) {
			if (frm.doc.employees[d].employee) {
				emp.push(frm.doc.employees[d].employee);
			}
		}
		frm.set_query("employee", "employees", function () {
			return {
				filters: {
					name: ["NOT IN", emp],
					status: "Active"
				}
			};
		});
	}
});

frappe.ui.form.on("Training Event Employee", {
	employee: function(frm) {
		frm.events.set_employee_query(frm);
	},
	create_travel_request: function(frm, cdt, cdn){
		var item = locals[cdt][cdn];
		// Follwoing line temporarily replaced by SHIV on 2020/09/17, need to restore back
		if (frm.doc.docstatus == 1 && (item.travel_request == '' || item.travel_request == undefined)) {
				frappe.flags.employee = item.employee;
				frappe.model.open_mapped_doc({
					method: "hrms.hr.doctype.training_event.training_event.create_travel_request",
					frm: cur_frm,
					args: {"employee": item.employee, "child_ref": item.name}
				})
		}
	}
});
