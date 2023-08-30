// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee PMS Evaluator Mapper', {
	refresh: function(frm) {
		frm.set_df_property('get_all_employees','hidden', frm.doc.employees.length > 0);
		frm.refresh_fields();
	},
	get_all_employees: function(frm){
		frappe.call({
			method: "get_employees",
			doc: frm.doc,
			callback: function(r){
				frm.refresh_fields();
			}
		})
	}
});
frappe.ui.form.on('PMS Evaluator Employees', {
	employees_add: function(frm) {
		frm.set_df_property('get_all_employees','hidden', frm.doc.employees.length > 0);
		frm.refresh_fields();
	},
	employees_remove: function(frm) {
		frm.set_df_property('get_all_employees','hidden', frm.doc.employees.length > 0);
		frm.refresh_fields();
	}
});
