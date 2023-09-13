// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee PMS Evaluator Mapper', {
	get_all_employees: function(frm){
		frappe.call({
			method: "get_employees",
			doc: frm.doc,
			callback: function(r){
				frm.refresh_fields();
			}
		})
	},
	get_all_mr_employees: function(frm){
		frappe.call({
			method: "get_mr_employees",
			doc: frm.doc,
			callback: function(r){
				frm.refresh_fields();
			}
		})
	},
	evaluator: function (frm) {
		frappe.call({
			method: "get_employee_name",
			doc: frm.doc,
			callback: (r) => {
				// frm.refresh_fields('evaluator_name');
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

frappe.ui.form.on('PMS Evaluator MR Employee', {
	employees_add: function(frm) {
		frm.set_df_property('get_all_mr_employees','hidden', frm.doc.mr_employees.length > 0);
		frm.refresh_fields();
	},
	employees_remove: function(frm) {
		frm.set_df_property('get_all_mr_employees','hidden', frm.doc.mr_employees.length > 0);
		frm.refresh_fields();
	}
});
