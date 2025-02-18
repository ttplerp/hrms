// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dispatch', {
	// refresh: function(frm) {

	// }
	onload: function (frm) {
		// Ver 2.0 Begins, following code added by SHIV on 28/11/2017
		if(frm.is_new()) {
			frappe.call({
				method: "erpnext.custom_utils.get_user_info",
				args: {"user": frappe.session.user},
				callback(r) {
					cur_frm.set_value("company", r.message.company);
				}
			});
		}
	},
	setup: function (frm) {
		frm.set_query("dispatch_format", function () {
			return {
				"filters": {
					"company": frm.doc.company
				}
			};
		});
	}
});
