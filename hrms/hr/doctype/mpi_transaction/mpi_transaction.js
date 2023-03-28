// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('MPI Transaction', {
	refresh: function(frm) {

	},
	fiscal_year:function(frm){
		frm.clear_table("items");
		frm.refresh_fields()
	},
	get_mpi_details:function(frm){
		frappe.call({
			method:"get_mpi_details",
			doc:frm.doc,
			callback:function(r){
				frm.refresh_fields()
				frm.dirty()
			}
		})
	}
});
