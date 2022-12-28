// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("project", "cost_center", "cost_center")
cur_frm.add_fetch("cost_center", "branch", "branch")

frappe.ui.form.on('MusterRoll Application', {
	setup: function(frm) {
		frm.get_docfield("items").allow_bulk_edit = 1;
	},
	refresh: function(frm) {

	},
	onload: function(frm) {
		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today());
		}
		frm.set_query("approver", function() {
			return {
				query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
				filters: {
					employee: frm.doc.requested_by
				}
			};
		}); 
	},
	// Ver 3.0 Begins, by SHIV on 2018/11/03
	// Following code commented by SHIV on 2018/11/03
	/*
	branch: function(frm){
		// Update Cost Center
		if(frm.doc.branch){
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Cost Center',
					filters: {
						'branch': frm.doc.branch
					},
					fieldname: ['name']
				},
				callback: function(r){
					if(r.message){
						cur_frm.set_value("cost_center", r.message.name);
						refresh_field('cost_center');
					}
				}
			});
		}
	},
	*/
	// Follwoing code added by SHIV on 2018/11/03
	branch: function(frm){
		update_requesting_info(frm.doc);
	},
	cost_center: function(frm){
		update_requesting_info(frm.doc);
	},
	project: function(frm){
		update_requesting_info(frm.doc);
	},
	// Ver 3.0 Ends
	get_employees: function(frm) {
		//load_accounts(frm.doc.company)
		return frappe.call({
			method: "get_employees",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("items");
				frm.refresh_fields();
			}
		});
	}

});

// Ver 3.0 Begins, Following code added by SHIV on 2018/11/03
var update_requesting_info = function(doc){
	cur_frm.call({
		method: "update_requesting_info",
		doc: doc
	});
}
// Ver 3.0 Ends

frappe.ui.form.on('MusterRoll Application Item', {
	"rate_per_day": function(frm, cdt, cdn) {
		doc = locals[cdt][cdn]
		if(doc.rate_per_day) {
			frappe.model.set_value(cdt, cdn, "rate_per_hour", (doc.rate_per_day * 1.5) / 8)
			cur_frm.refresh_field("rate_per_hour")
		}
	},
	"existing_cid": function(frm, cdt, cdn){
		var child  = locals[cdt][cdn];

		frappe.call({
			method: "frappe.client.get_value",
			args: {doctype: "Muster Roll Employee", fieldname: ["person_name", "rate_per_day", "rate_per_hour"],
					filters: {
								name: child.existing_cid
					}},
			callback: function(r){
				frappe.model.set_value(cdt, cdn, "person_name", r.message.person_name);
				frappe.model.set_value(cdt, cdn, "rate_per_day", r.message.rate_per_day);
				frappe.model.set_value(cdt, cdn, "rate_per_hour", r.message.rate_per_hour);
			}
		})
	},	
})
