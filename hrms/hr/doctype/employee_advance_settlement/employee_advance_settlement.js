// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Advance Settlement', {
	onload: (frm) => {
		frm.set_query("item_code", "items", function(doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            return {
                filters: {
                    "item_group": row.item_group
                }
            };
        });
	},
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

	expense_branch: function(frm) {
		set_branch_child(frm);
		frappe.call({
			method: "get_cost_center",
			doc: frm.doc,
			callback: function (r) {
				frm.doc.items.forEach(e => {
					e.cost_center = r.message;
				})
			}
		})
		frm.refresh_field('items')
	}
});

frappe.ui.form.on('Employee Advance Settlement Item', {
	item_code:function(frm,cdt,cdn){
		update_expense_account(frm, cdt, cdn);
	}
})

var update_expense_account = function(frm, cdt, cdn){
	let row = locals[cdt][cdn];
	if(row.item_code){
		frappe.call({
			method: "hrms.hr.doctype.employee_advance_settlement.employee_advance_settlement.get_expense_account",
			args: {
				"company": frm.doc.company,
				"item": row.item_code,
			},
			callback: function(r){
				console.log(r.message)
				frappe.model.set_value(cdt, cdn, "account", r.message);
				cur_frm.refresh_field(cdt, cdn, "account");
			}
		})
	}
}

var set_branch_child = function (frm) {
	frm.doc.items.forEach(el => {
		el.branch = frm.doc.expense_branch;
	});
	frm.refresh_field('items')
}
