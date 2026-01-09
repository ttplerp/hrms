// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('GST Invoice', {
	refresh: function(frm) {
		if (frm.doc.cbs_response !== 'SUCCESS' && frm.doc.docstatus === 1) {
			frm.add_custom_button(__('Make CBS Entry'), function() {
				frappe.confirm(
					__('Confirm for CBS Entry.'),
					() => {
						frm.call({
							method: 'make_cbs_entry',
							doc: frm.doc,
							callback: function (r) {
								// console.log(r);
								if (!r.exc) {
									frm.reload_doc();
								}
							}
						});
					}, 
					() => {
						console.log("Operation is cancelled.")
					}
				);
			}).addClass("btn-primary");
		}
	},
	
});

frappe.ui.form.on('GST Invoice Item', {
	total_amount: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.total_amount) {
			// calculate 5% gst and actual amount
			// actual amount = total_amount / 1.05; derived from, total_amount = actual_amount (1 + gst_rate)
			let actual_amount = row.total_amount / 1.05;
			let gst_amount = row.total_amount - actual_amount;

			frappe.model.set_value(cdt, cdn, 'fee_charges', actual_amount);
			frappe.model.set_value(cdt, cdn, 'gst', gst_amount);
		} else {
			frappe.model.set_value(cdt, cdn, 'fee_charges', 0);
			frappe.model.set_value(cdt, cdn, 'gst', 0);
		}
	}

});