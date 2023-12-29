// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Leave Encashment', {
	setup: function(frm) {
		frm.set_query("leave_period", function() {
			return {
				filters: {
					is_active: 1
				}
			}
		});

		frm.set_query("leave_type", function() {
			return {
				filters: {
					allow_encashment: 1
				}
			}
		});
	},
	get_employees: function(frm) {
		if(frm.doc.docstatus == 0 && frm.doc.leave_type && frm.doc.leave_period) {
			return frappe.call({
				method: "get_employees",
				doc: frm.doc,
				callback: function(r, rt) {
					frm.refresh_field("items");
					frm.refresh_fields();
				}
			});
		}
	}
});