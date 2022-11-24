// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salary Increment', {
	onload: function(frm){
		if(frm.doc.__islocal){
			frm.set_value("fiscal_year", frappe.sys_defaults.fiscal_year);
		}
	},
	
	employee: function(frm){
		get_employee_payscale(frm.doc);
	},
	
	fiscal_year: function(frm){
		get_employee_payscale(frm.doc);
	},
	
	month: function(frm){
		get_employee_payscale(frm.doc);
	},
	
	increment: function(frm){
		var old_basic = flt((frm.doc.old_basic)?frm.doc.old_basic:0);
		var increment = flt((frm.doc.increment)?frm.doc.increment:0);
		
		if (old_basic){
			frm.set_value("new_basic",(old_basic+increment));
		}
	},
});

var get_employee_payscale = function(doc){
	cur_frm.call({
		method: "get_employee_payscale",
		doc: doc
	});
}
