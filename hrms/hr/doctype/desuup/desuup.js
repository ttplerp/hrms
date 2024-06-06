// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Desuup', {
	// refresh: function(frm) {

	// }
	onload: function(frm) {
		frm.set_query('bank_branch', function(doc) {
			return {
				filters: {
					"financial_institution": doc.bank_name
				}
			};
		});
	}
});
