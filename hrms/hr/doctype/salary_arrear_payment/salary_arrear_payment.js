// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salary Arrear Payment', {

	refresh: function(frm) {
		if(frm.doc.docstatus == 1){
			frm.events.add_bank_entry_button(frm);
		}

	},
	add_bank_entry_button: function(frm) {
		frappe.call({
			method: 'hrms.hr.doctype.salary_arrear_payment.salary_arrear_payment.arrear_payment_has_bank_entries',
			args: {
				'name': frm.doc.name
			},
			callback: function(r) {
				if (r.message && !r.message.submitted) {
					//following line is replaced with subsequent by SHIV on 2020/10/21
					//frm.add_custom_button("Make Bank Entry", function() {
					frm.add_custom_button("Make Accounting Entries", function() {
						make_accounting_entry(frm);
					}).addClass("btn-primary");
				}
			}
		});
	},
	"get_employees": function(frm) {
		if(frm.doc.docstatus != 0) return;
		if(frm.doc.fiscal_year) {
			refresh_many(["items"]);
			return frappe.call({
				method: "get_employees",
				doc: frm.doc,
				callback: function(r, rt) {
					frm.refresh_field("items");
					frm.refresh_fields();
				},
				freeze: true,
            	freeze_message: "Loading Details..... Please Wait"
			});
		}
		else {
			msgprint("Select Fiscal Year First")
		}
	},
});
let make_accounting_entry = function (frm) {
	var doc = frm.doc;

	return frappe.call({
		doc: cur_frm.doc,
		method: "make_accounting_entry",
		callback: function() {
			// frappe.set_route(
			// 	'List', 'Journal Entry', {"Journal Entry Account.reference_name": frm.doc.name}
			// );
			frappe.set_route(
				'List', 'Journal Entry', {"reference_type": frm.doc.doctype, "reference_name": frm.doc.name}
			);
		},
		freeze: true,
		freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Creating Payment Entries...</span>'
	});
};