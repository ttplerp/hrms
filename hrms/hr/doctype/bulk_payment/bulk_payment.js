// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Payment', {
	onload: function(frm) {
		let grid = frm.fields_dict['items'].grid;
        grid.cannot_add_rows = true;

		frm.doc.from_date = frappe.datetime.add_days(frappe.datetime.nowdate(), -30);
		frm.refresh_field('from_date');
	},

	refresh: function(frm) {
		if (frm.doc.docstatus != 1 && frm.doc.docstatus != 2) {
			frm.add_custom_button(__("Get Transactions"), function () {
				frm.events.get_reference_details(frm);
			}).toggleClass("btn-primary", !(frm.doc.employees || []).length);
		}
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
