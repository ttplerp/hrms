// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Update Bank Account', {
	onload: function(frm) {
		frm.set_query('bank_branch', function(doc) {
			return {
				filters: {
					"financial_institution": doc.bank_name
				}
			};
		});
	}
	// refresh: function(frm) {

	// }
});
