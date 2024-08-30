// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Daily Activity Log', {
	// refresh: function(frm) {

	// },
});

frappe.ui.form.on('Daily Activity Log Item', {
	// refresh: function(frm) {

	// },
	start_time: function(frm, cdt, cdn){
		var row = locals[cdt][cdn]
		if(row.start_time && row.end_time){
			// var hours = moment(row.end_time).diff(moment(row.start_time), "seconds") / 3600;
			frappe.call({
				method: "calculate_duration",
				doc: frm.doc,
				args: {"start_time": row.start_time, "end_time": row.end_time},
				callback: function(r){
					if(r.message){
						frappe.model.set_value(cdt, cdn, "duration", r.message);
						frm.refresh_field("activities");
					}
				}
			})
		}
	},
	end_time: function(frm, cdt, cdn){
		var row = locals[cdt][cdn]
		if(row.start_time && row.end_time){
			// var hours = moment(row.end_time).diff(moment(row.start_time), "seconds") / 3600;
			frappe.call({
				method: "calculate_duration",
				doc: frm.doc,
				args: {"start_time": row.start_time, "end_time": row.end_time},
				callback: function(r){
					if(r.message){
						frappe.model.set_value(cdt, cdn, "duration", r.message);
						frm.refresh_field("activities");
					}
				}
			})
		}
	}
});
