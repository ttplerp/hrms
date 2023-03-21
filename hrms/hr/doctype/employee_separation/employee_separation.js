// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Separation', {
	setup: function(frm) {
		frm.add_fetch("employee_separation_template", "company", "company");
		frm.add_fetch("employee_separation_template", "department", "department");
		frm.add_fetch("employee_separation_template", "designation", "designation");
		frm.add_fetch("employee_separation_template", "employee_grade", "employee_grade");
	},

	onload_post_render: function(frm){

	},
	refresh: function(frm) {
		if(cur_frm.doc.docstatus == 1 && cur_frm.doc.employee_benefits_status == "Not Claimed" && cur_frm.doc.clearance_acquired == 1){
			frm.add_custom_button("Create Employee Benefit", function(){
				frappe.model.open_mapped_doc({
					method: "hrms.hr.doctype.employee_separation.employee_separation.make_employee_benefit",
					frm: me.frm
				})
			});
		}
		if(cur_frm.doc.docstatus == 1 && cur_frm.doc.employee_benefits_status == "Not Claimed" && cur_frm.doc.clearance_acquired == 0){
			frm.add_custom_button("Create Employee Clearance", function(){
				frappe.model.open_mapped_doc({
					method: "hrms.hr.doctype.employee_separation.employee_separation.make_separation_clearance",
					frm: me.frm
				})
			});
		}
	},

	employee_separation_template: function(frm) {
		frm.set_value("activities" ,"");
		if (frm.doc.employee_separation_template) {
			frappe.call({
				method: "erpnext.controllers.employee_boarding_controller.get_onboarding_details",
				args: {
					"parent": frm.doc.employee_separation_template,
					"parenttype": "Employee Separation Template"
				},
				callback: function(r) {
					if (r.message) {
						$.each(r.message, function(i, d) {
							var row = frappe.model.add_child(frm.doc, "Employee Boarding Activity", "activities");
							$.extend(row, d);
						});
					}
					refresh_field("activities");
				}
			});
		}
	},

	reason_for_resignation: function(frm){
		var fields = ["Superannuation", "Demise"];
		frm.toggle_reqd("q24", !fields.includes(frm.doc.reason_for_resignation));
	}
});
