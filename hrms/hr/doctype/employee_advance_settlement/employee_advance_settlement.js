// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Advance Settlement', {
	setup: function(frm){
		if (frm.doc.employee && frm.doc.__islocal){
			frappe.call({
				method: "get_advance_details",
				doc: frm.doc,
				callback: function(r){
					frm.refresh_field("total_deductible_amount")
					frm.refresh_field("total_deducted_amount")
					frm.refresh_field("balance_amount")
					frm.refresh_field("settlement_amount")
				}
			})
		}
	},

	refresh: function(frm) {
		if(frm.doc.docstatus === 1){
			frm.add_custom_button(__('View General Ledger'), function() {
				frappe.route_options = {
					"voucher_no": frm.doc.name,
					"from_date": frm.doc.posting_date,
					"to_date": frm.doc.posting_date,
					"company": frm.doc.company,
					"group_by_voucher": 0
				};
				frappe.set_route("query-report", "General Ledger");
			});
		}
	},

	edit_posting_date: function(frm){
		frm.set_df_property('posting_date','read_only', !frm.doc.edit_posting_date)
	},
});
