// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'hrms/hr/employee_property_update.js' %}

frappe.ui.form.on('Employee Promotion', {
	refresh: function(frm) {
	},
	get_details: function(frm) {
		if(!frm.doc.employee){
			frappe.throw("Please select Employee first.")
		}
		frappe.call({
			method:"get_promotion_details",
			doc: frm.doc,
			args:{"employee":frm.doc.employee},
			callback: function(r){
				if(r.message){
					var rows = frappe.model.add_child(frm.doc, "Employee Property History", "promotion_details");
					rows.property = r.message[0]['property'];
					rows.current = r.message[0]['current'];
					rows.new = r.message[0]['new'];
					rows.fieldname = r.message[0]['fieldname'];

				}
				refresh_field("promotion_details");
			}
		})
	}
});
