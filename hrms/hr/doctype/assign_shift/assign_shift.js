// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Assign Shift', {
	"get_employees": function(frm){
		get_employees(frm)
	},
	apply_to_all: function(frm){
		apply_to_all(frm)
	}
});

frappe.ui.form.on('Shift Details', {
	"29": function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row['29']==1){
			check_date(frm, cdt, cdn, "29");
		}
	},
	"30": function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row['30']==1){
			check_date(frm, cdt, cdn, "30");
		}
	},
	"31": function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row['31']==1){
			check_date(frm, cdt, cdn, "31");
		}
	},
});

function check_date(frm, cdt, cdn, date){
	var row = locals[cdt][cdn];
	frappe.call({
		method: "check_date",
		doc: frm.doc,
		args: {"date": date},
		callback: function(r){
			if(r.message){
				if(r.message == "no"){
					frappe.model.set_value(cdt,cdn,String(date),0);
					frm.refresh_fields();
					frappe.msgprint("Date "+date+" doesn't exist for the month "+frm.doc.month+" in the year "+frm.doc.fiscal_year);
				}
			}
		}
	})
}
function get_employees(frm){
	return frappe.call({
		method: "get_employees",
		doc: cur_frm.doc,
		callback: function(r, rt) {
			frm.refresh_field("shift_details");
			frm.refresh_fields();
		}
	});     
}

cur_frm.fields_dict['shift_details'].grid.get_field('employee').get_query = function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	return {
		filters: {
			"reports_to": cur_frm.doc.supervisor
		}
	}
}

function apply_to_all(frm){
	var items = frm.doc.shift_details
	if (frm.doc.apply_to_all){
		items.map(function(rows){
			rows.mark_attendance = 1
		})
	}else{
		items.map(function(rows){
			rows.mark_attendance = 0
		})
	}
	refresh_field('shift_details')
}