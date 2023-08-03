// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Transfer Request', {
	refresh: function(frm) {
		frm.set_query("employee",function(doc) {
			return {
				query: "erpnext.controllers.queries.filter_division_employees",
				filters: {
					'user': frappe.session.user
				}
			}
		});
		if (frm.doc.docstatus == 1) {
			frappe.call({
				method:"check_employee_transfer",
				doc: frm.doc,
				callback: function(r){
					if(r.message==0){
						frm.add_custom_button(__("Employee Transfer"),
						() => frm.events.make_employee_transfer(frm), __("Make"));
					}
				}
			})

		}
	},
	make_employee_transfer: function (frm) {
		frappe.model.open_mapped_doc({
			method: "hrms.hr.doctype.employee_transfer_request.employee_transfer_request.make_employee_transfer",
			frm: frm,
			run_link_triggers: true
		});
	},

	employee: function(frm){
		frappe.call({
			method: "validate_requested_by",
			doc: frm.doc
		})
		frappe.call({
			method: "get_employee_details",
			doc: frm.doc,
			callback: function(r){
				frm.set_value("designation", r.message[0])
				frm.set_value("branch", r.message[1])
				frm.set_value("employee_name", r.message[2])
				frm.set_value("division", r.message[3])
				frm.set_value("cell_number", r.message[4])
				frm.set_value("email", r.message[5])
				frm.refresh_fields();
			}
		})
	}
});
