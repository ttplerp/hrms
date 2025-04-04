// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Payment', {
	onload: function(frm) {
		let grid = frm.fields_dict['items'].grid;
        grid.cannot_add_rows = true;

		frm.doc.from_date = frappe.datetime.add_days(frappe.datetime.nowdate(), -30);
		frm.refresh_field('from_date');

		create_custom_buttons(frm);

	},

	refresh: function(frm) {
		if (frm.doc.docstatus != 1 && frm.doc.docstatus != 2) {
			frm.add_custom_button(__("Get Transactions"), function () {
				frm.events.get_reference_details(frm);
			}).toggleClass("btn-primary", !(frm.doc.employees || []).length);
		}

		create_custom_buttons(frm);

	},

	from_date: function(frm) {
		frm.events.clear_items_table(frm);
	},

	to_date: function(frm) {
		frm.events.clear_items_table(frm);
	},

	get_reference_details: function (frm) {
		return frappe
			.call({
				doc: frm.doc,
				method: "fill_reference_details",
				freeze: true,
				freeze_message: __("Fetching Transactions"),
			})
			.then((r) => {
				if (r.docs?.[0]?.items) {
					frm.dirty();
					// frm.save();
				}
				frm.refresh();
				frm.scroll_to_field("items");
			});
	},

	clear_items_table: function (frm) {
		frm.clear_table("items");
		frm.refresh();
	},
});

/* ePayment Begins */
var create_custom_buttons = function(frm){
	if(frm.doc.docstatus == 1){
		if(!frm.doc.payment_status || frm.doc.payment_status == 'Failed' || frm.doc.payment_status == 'Payment Failed'){
			frm.page.set_primary_action(__('Process Payment'), () => {
				frappe.model.open_mapped_doc({
					method: "hrms.hr.doctype.bulk_payment.bulk_payment.make_bank_payment",
					frm: cur_frm
				});
			});
		}
	}
}
/* ePayment Ends */
