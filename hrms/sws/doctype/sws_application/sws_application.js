// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('SWS Application', {
	refresh: function(frm) {
		if(!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today())
		}
	},
	onload: function(frm){
		frappe.call({
			method: "get_sws_accounts",
			doc: frm.doc,
			callback: function(r){
				if(r.message){
					frm.set_value("credit_account", r.message[0]);
					frm.set_value("debit_account", r.message[1]);
					frm.refresh_field("credit_account");
					frm.refresh_field("debit_account");
				}
			}
		})
	}
});
frappe.ui.form.on('SWS Application Item', {
	reference_document: function(frm,cdt, cdn){
		var row = locals[cdt][cdn];
		frappe.call({
			method: "get_member_details",
			doc: frm.doc,
			args: {
				"name": row.reference_document
			},
			callback: function(r){
				if(r.message){
					frappe.model.set_value(cdt, cdn, "relationship", r.message[0]);
					frappe.model.set_value(cdt, cdn, "cid_no", r.message[1]);
					frappe.model.set_value(cdt, cdn, "full_name", r.message[2]);
				}
				frm.refresh_field("items");
			}
		});
	},
	sws_event: function(frm, cdt, cdn) {
				var row = locals[cdt][cdn];
				if(!row.reference_document){
						frappe.throw("Please select reference document first.")
				}
				if(row.sws_event == "" || row.sws_event == null){
						frappe.model.set_value(cdt, cdn, "claim_amount",null);
						frm.model.set_value(cdt, cdn, "amount", null);
				}
				frappe.call({
						method: "hrms.sws.doctype.sws_application.sws_application.get_event_amount",
						args: {"sws_event":row.sws_event, "reference":row.reference_document, "employee":frm.doc.employee},
						callback: function(r){
								if(r.message){
										console.log(r.message)
										frappe.model.set_value(cdt, cdn, "claim_amount", r.message[0]['amount']);
										frappe.model.set_value(cdt, cdn, "amount", r.message[0]['amount']);
										frm.refresh_field("claim_amount");
										frm.refresh_field("amount");
								}
						}
				})
	},
});

cur_frm.fields_dict['items'].grid.get_field('reference_document').get_query = function(frm, cdt, cdn) {
	if (!frm.employee) {
				frm.employee = "dhskhfgskhfgsfhksfsjhbaf"
		}
		return {
				query : "erpnext.controllers.queries.filter_sws_member_item",
				filters: {
						"employee": frm.employee,
						"docstatus": 1,
						"status": "Active"
				}
		}
}