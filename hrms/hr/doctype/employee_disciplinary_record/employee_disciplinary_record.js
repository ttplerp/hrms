// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Disciplinary Record', {
	refresh: function(frm) {
		if(frm.doc.docstatus == "0"){
                        frm.set_df_property("not_guilty_or_acquitted", "hidden", 1);
                }

	},
	"from_date": function(frm) {
		validate_date(frm);
	},
	"to_date": function(frm) {
		validate_date(frm);
	},
});

function validate_date(frm) {
        if(frm.doc.to_date && frm.doc.from_date){
                var date1 = new Date(frm.doc.from_date);
                var date2 = new Date(frm.doc.to_date);
                var today = new Date();

                if(date2 < today){
                        frappe.msgprint("The Suspension date cannot be past date");
			cur_frm.set_value("to_date","");
                }

                if(date1 > date2){
                        frappe.msgprint("To date Cannot be before From Date ");
			cur_frm.set_value("from_date","");
			cur_frm.set_value("to_date","");
                }
	}
}
