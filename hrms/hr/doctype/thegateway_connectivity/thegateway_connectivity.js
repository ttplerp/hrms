// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('TheGateway Connectivity', {
	refresh: function(frm) {

	},
	test_connectivity: function(frm){	
		return frappe.call({
			method: "hrms.hr.doctype.selected_candidate.selected_candidate.get_token",
			callback: function (b) {
				if (b.message) { 
					frappe.msgprint("Connection successfull.")
				}
			},
			freeze: true,
			freeze_message: 'Connecting...'
		});
	}
});
