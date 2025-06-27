// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("project", "cost_center", "cost_center")
cur_frm.add_fetch("branch", "cost_center", "cost_center")

frappe.ui.form.on('Muster Roll Application', {
	refresh: function(frm) {
		frm.set_query("unit", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"disabled":0,
					"is_division":0,
					"is_unit":1,
					"is_section":0
				}
			};
		});
		frm.set_query("from_unit", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"disabled":0,
					"is_division":0,
					"is_unit":1,
					"is_section":0
				}
			};
		});
		// frm.fields_dict['items'].grid.get_field('CHILD_FIELD_NAME_TO_BE_FILTERED').get_query = function(doc, cdt, cdn) {
		// 	var child = locals[cdt][cdn];
		// 	//console.log(child);
		// 	return {    
		// 		filters:[
		// 			['IS_IT_OK_FIELD', '=', child.CHECKBOX_FIELD]
		// 		]
		// 	}
		// }
		frm.set_query("section", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"disabled":0,
					"is_division":0,
					"is_unit":0,
					"is_section":1
				}
			};
		});
		frm.fields_dict['items'].grid.get_field('bank_branch').get_query = function(doc, cdt, cdn) {
			var child = locals[cdt][cdn];
			console.log("pl");
			return {    
				filters:[
					['financial_institution', '=', child.bank]
				]
			}
		}
	},
	onload: function(frm) {
		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today());
		}
	},
	requested_by: function(frm){
		if (frm.doc.requested_by){
			frappe.call({
				method: "hrms.hr.doctype.muster_roll_application.muster_roll_application.get_mr_approvers",
				args: {
					employee: frm.doc.requested_by,
				},
				callback: function(r) {
					if(r.message) {
						frm.set_value("approver", r.message[0])
						frm.set_value("approver_name", r.message[1])
						frm.refresh_fields("approver")
						frm.refresh_fields("approver_name")
					}
				}
			});
		}
	},

	branch: function(frm){
		update_requesting_info(frm.doc);
	},
	cost_center: function(frm){
		update_requesting_info(frm.doc);
	},
	project: function(frm){
		update_requesting_info(frm.doc);
	},
	get_employees: function(frm) {
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

var update_requesting_info = function(doc){
	cur_frm.call({
		method: "update_requesting_info",
		doc: doc
	});
}

frappe.ui.form.on('Muster Roll Application Item', {
	"rate_per_day": function(frm, cdt, cdn) {
		console.log("heree")
		var item = locals[cdt][cdn]
		if(item.rate_per_day) {
			frappe.model.set_value(cdt, cdn, "rate_per_hour_normal", (item.rate_per_day ) / 8)
			frm.refresh_field("rate_per_hour_normal")
			frappe.model.set_value(cdt, cdn, "rate_per_hour", (item.rate_per_day * 1.5) / 8)
			frm.refresh_field("rate_per_hour")
		}
	},
	"existing_cid": function(frm, cdt, cdn){
		var child  = locals[cdt][cdn];
		frappe.call({
			method: "frappe.client.get_value",
			args: {doctype: "Muster Roll Employee", fieldname: ["person_name", "rate_per_day", "rate_per_hour_overtime","rate_per_hour_normal"],
				filters: {
					name: child.existing_cid
				}},
			callback: function(r){
				frappe.model.set_value(cdt, cdn, "person_name", r.message.person_name);
				frappe.model.set_value(cdt, cdn, "rate_per_day", r.message.rate_per_day);
				frappe.model.set_value(cdt, cdn, "rate_per_hour", r.message.rate_per_hour_overtime);
				frappe.model.set_value(cdt, cdn, "rate_per_hour_normal", r.message.rate_per_hour_normal);
			}

		})
	},
	
})
