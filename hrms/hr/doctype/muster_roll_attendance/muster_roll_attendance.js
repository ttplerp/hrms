// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Muster Roll Attendance', {
	refresh: function(frm) {
		frm.set_query('mr_employee', function(doc) {
			return {
				filters: {
					"status": "Active"
				}
			};
		});
	}
});
