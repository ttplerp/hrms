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
		
		frm.fields_dict.items.grid.get_field("account").get_query = function(doc) {
            return {
                filters: {
                    "is_group": 0
                }
            };
        }
	},
	tds_percent: function(frm){
		frappe.call({
			method: "get_tds_account",
			doc: frm.doc,
			callback: function(r){
				if(r.message){
					frm.set_value("tds_account", r.message);
				}
			}
		})
		// frappe.call({
		// 	method: "get_tds_account",
		// 	doc: frm.doc,
		// 	callback: function(r){
		// 		if(r.message){
		// 			frm.set_value("tds_account", r.message);
		// 		}
		// 	}
		// })
		frm.refresh_field("tds_account");
	},
	advance_type: function(frm){
		frappe.call({
			method: "get_credit_account",
			doc: frm.doc,
			callback: function(r){
				if(r.message){
					frm.set_value("credit_account", r.message);
				}
			}
		})
		frm.refresh_field("tds_account");
	},
	edit_posting_date: function(frm){
		frm.set_df_property('posting_date','read_only', !frm.doc.edit_posting_date)
	},
});
