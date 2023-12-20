// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Batch Data Communication', {
	get_employees: function(frm){
		frm.clear_table("items");
		frappe.call({
			method: "get_employees",
			doc: cur_frm.doc,
			args: {"branch": frm.doc.branch},
			callback: function(r, rt){
				if(r.message){
					// r.message.forEach(function(v){
					// var rows = frappe.model.add_child(frm.doc, "Batch Data Communication Item","items");
					// rows.employee = v['employee'];
					// rows.employee_name = v['employee_name'];
					// // rows.uom = v['uom'];
					// // rows.qty = v['qty'] * row.qty;
					// });
				}
				refresh_field("employees");
			}

		})
	},
});

frappe.ui.form.on("Batch Data Communication", "before_submit", function(frm, cdt, cdn) {
	alert('Please make sure the data in this transaction is correct before submitting');
	return false;
	})
