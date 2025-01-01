// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Merge CL To EL', {
	setup: function (frm) {
		frm.get_field('items').grid.editable_fields = [
			{ fieldname: 'employee', columns: 2 },
			{ fieldname: 'employee_name', columns: 2 },
			{ fieldname: 'leaves_allocated', columns: 2 },
			{ fieldname: 'leaves_taken', columns: 2 },
			{ fieldname: 'leave_balance', columns: 2 }
		];
	},
	"get_details": function (frm) {
		return frappe.call({
			method: "get_data",
			doc: frm.doc,
			callback: function (r, rt) {
				frm.refresh_field("items");
				frm.refresh_fields();
			}
		});
	}
});
