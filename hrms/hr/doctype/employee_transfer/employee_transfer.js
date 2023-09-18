// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


frappe.ui.form.on('Employee Transfer', {
	onload:function(frm) {
		frm.set_query("new_department", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"is_section":0,
					"is_division": 0,
					"is_unit":0
				}
			};
		});
		frm.set_query("new_division", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"parent_department":frm.doc.new_department,
					"disabled":0,
					"is_division":1,
					"is_section":0,
				}
			};
		});
		frm.set_query("new_section", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"parent_department":frm.doc.new_division,
					"disabled":0,
					"is_division":0,
					"is_section":1
				}
			};
		});
		frm.set_query("new_unit", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"parent_department":frm.doc.new_section,
					"disabled":0,
					"is_division":0,
					"is_section":0,
					"is_unit": 1
				}
			};
		});
	},
	refresh: function(frm) {
		enable_disable(frm);
		if(cur_frm.doc.docstatus == 1 && cur_frm.doc.employee_benefits_status == "Not Claimed"){
			frm.add_custom_button("Create Employee Benefits", function(){
				frappe.model.open_mapped_doc({
					method: "hrms.hr.doctype.employee_transfer.employee_transfer.make_employee_benefit",
					frm: me.frm
				})
			});
		}
	},
	new_department: function(frm){
		frm.set_value("new_division", null);
		frm.set_value("new_section", null);
		// frm.set_value("new_branch", null);
		// frm.set_value("new_cost_center", null);
		frm.set_value("new_reports_to", null)
	},
	new_division: function(frm){
		frm.set_value("new_section", null);
		// frm.set_value("new_branch", null);
		// frm.set_value("new_cost_center", null);
	},
	// workflow_state: function(frm) {
	// 	if(frm.doc.workflow_state == "Rejected"){
	// 		frm.doc.toggle_reqd("Rejection Reason",1);
	// 	}

	// }
});

var enable_disable = function(frm){
	if(in_list(frappe.user_roles, "Administrator") || in_list(frappe.user_roles, "HR User") ||
		in_list(frappe.user_roles, "HR Manager")){
		frm.toggle_reqd(["new_department", "new_reports_to"], 1);
	} else {
		frm.toggle_display(["old_department", "old_division", "old_section", "old_reports_to", "current_supervisor_name",
			"new_department", "new_division", "new_section", "new_reports_to"], 0);
	}
}
