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
		// console.log(cur_frm.doc.sb_exit_interview)
		// if (frm.doc.docstatus === 1 && frappe.user.has_role(["HR User"])){
		// 	cur_frm.set_df_property("sb_exit_interview","hidden",0);
		// }
		// else if(frm.doc.docstatus === 1){
		// 	cur_frm.set_df_property("sb_exit_interview","hidden",1);
		// }
		// frm.refresh_fields()

	},
	refresh: function(frm) {
		// if(cur_frm.doc.docstatus == 1 && cur_frm.doc.employee_benefits_status == "Not Claimed" && cur_frm.doc.clearance_acquired == 1){
		// 	frm.add_custom_button("Create Employee Benefit", function(){
		// 		frappe.model.open_mapped_doc({
		// 			method: "hrms.hr.doctype.employee_separation.employee_separation.make_employee_benefit",
		// 			frm: me.frm
		// 		})
		// 	});
		// }
		// if(cur_frm.doc.docstatus == 1 && cur_frm.doc.employee_benefits_status == "Not Claimed" && cur_frm.doc.clearance_acquired == 0){
		// 	frm.add_custom_button("Create Employee Clearance", function(){
		// 		frappe.model.open_mapped_doc({
		// 			method: "hrms.hr.doctype.employee_separation.employee_separation.make_separation_clearance",
		// 			frm: me.frm
		// 		})
		// 	});
		// }
		if (frm.doc.docstatus == 1 && frm.doc.exit_interview == null){
			frm.add_custom_button(__('Exit Interview'), function(){
			frappe.model.open_mapped_doc({
					method: "hrms.hr.doctype.employee_separation.employee_separation.make_exit_interview",
					frm: cur_frm
				})
			}, __("Create"));
		}
		if(cur_frm.doc.docstatus == 1 && cur_frm.doc.employee_benefits_status == "Not Claimed" && cur_frm.doc.clearance_acquired == 1){
			frm.add_custom_button("Create Employee Benefit", function(){
				frappe.model.open_mapped_doc({
					method: "hrms.hr.doctype.employee_separation.employee_separation.make_employee_benefit",
					frm: cur_frm
				})
			});
		}
		if(cur_frm.doc.docstatus == 1 && cur_frm.doc.employee_benefits_status == "Not Claimed" && cur_frm.doc.clearance_acquired == 0 && cur_frm.doc.exit_interview){
			frm.add_custom_button("Create Employee Clearance", function(){
				frappe.model.open_mapped_doc({
					method: "hrms.hr.doctype.employee_separation.employee_separation.make_separation_clearance",
					frm: cur_frm
				})
			});
		}
		// if (frm.doc.project) {
		// 	frm.add_custom_button(__('Project'), function() {
		// 		frappe.set_route("Form", "Project", frm.doc.project);
		// 	},__("View"));
		// 	frm.add_custom_button(__('Task'), function() {
		// 		frappe.set_route('List', 'Task', {project: frm.doc.project});
		// 	},__("View"));
		// }
		// if (frm.doc.docstatus === 1 && frm.doc.project) {
		// 	frappe.call({
		// 		method: "erpnext.hr.utils.get_boarding_status",
		// 		args: {
		// 			"project": frm.doc.project
		// 		},
		// 		callback: function(r) {
		// 			if (r.message) {
		// 				frm.set_value('boarding_status', r.message);
		// 			}
		// 			refresh_field("boarding_status");
		// 		}
		// 	});
		// }
	},
	// superannuation: function(frm){
	// 	if(frm.doc.superannuation==1){
	// 		frm.set_df_property("q24","reqd",1);
	// 	}
	// 	else
	// 	{
	// 		frm.set_df_property("q24","reqd",0);
	// 	}
	// 	frm.refresh_fields();

	// },
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

	// employee: function(frm) {
	// 	if (frm.doc.employee) {				    
	// 		frappe.call({			
	// 		   method: 'get_training_obligation_list',
	// 		   doc: frm.doc,
	// 		   callback: (r)=> {
	// 			frm.refresh_field('obligation_history');
	// 			   frm.refresh_fields()				
	// 		   }
	// 	   })
	//    }	
	// },

	reason_for_resignation: function(frm){
		var fields = ["Superannuation", "Demise"];
		frm.toggle_reqd("q24", !fields.includes(frm.doc.reason_for_resignation));
	}
});
