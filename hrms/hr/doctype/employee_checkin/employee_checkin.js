// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.disable_save();

frappe.ui.form.on('Employee Checkin', {
	setup: (frm) => {
		if(!frm.doc.time) {
			frm.set_value("time", frappe.datetime.now_datetime());
		}
	},
	refresh: (frm) => {
		var d = new Date();
		if(d.getMonth() < 10){
			var date = d.getFullYear()+"-0"+d.getMonth()+"-"+d.getDate();
		}
		else{
			var date = d.getFullYear()+"-"+d.getMonth()+"-"+d.getDate();
		}
		var cd = new Date(d)
		var current_date = moment(cd).format("Y-mm-d");
		var n = moment(d).format("HH:MM:SS");
		console.log(current_date)
		frappe.call({
			method: "current_date_time",
			doc: frm.doc,
			args: {"shift": frm.doc.shift},
			callback: function(r){
				// console.log(r.message)
				// if(n > r.message[0]['office_out_start']){
				// 	console.log("here")
				// }
				// console.log(String(r.message[0].lunch_out_start))
				if(frm.doc.shift != null || frm.doc.shift != ''){
					var shift_end_time = r.message[0]['shift_end_time'];
				}
				var lunch_in_start = r.message[0]['lunch_in_start'];
				var lunch_out_start = r.message[0]['lunch_out_start'];
				var office_out_start = r.message[0]['office_out_start'];
				// var office_in_start = r.message[0]['office_in_start'];
				if(n > lunch_out_start && n < lunch_in_start && (!frm.doc.shift || frm.doc.shift == null || frm.doc.shift == '') && date == current_date){
					if(frm.doc.docstatus == 1) {
						frm.page.clear_primary_action();
						frm.add_custom_button(__("Lunch Out"),
							function() {
								frm.events.lunch_out(frm, n, lunch_out_start);
							}
						).toggleClass('btn-primary', !(frm.doc.employees || []).length);
					}
				}
				else if(n > lunch_in_start && n < office_out_start  && (!frm.doc.shift || frm.doc.shift == null || frm.doc.shift == '') && date == current_date){
					if(frm.doc.docstatus == 1) {
						frm.page.clear_primary_action();
						frm.add_custom_button(__("Lunch In"),
							function() {
							frm.events.lunch_in(frm, n, lunch_in_start);
							}
						).toggleClass('btn-primary', !(frm.doc.employees || []).length);
					}
				}
				else if(n >= office_out_start  && (!frm.doc.shift || frm.doc.shift == null || frm.doc.shift == '') && date == current_date){
					if(frm.doc.docstatus == 1) {
						frm.page.clear_primary_action();
						frm.add_custom_button(__("Office Out"),
							function() {
							frm.events.office_out(frm, n, office_out_start);
							}
						).toggleClass('btn-primary', !(frm.doc.employees || []).length);
					}
				}
				else{
					if(frm.doc.docstatus == 1 && date == current_date) {
						frm.page.clear_primary_action();
						frm.add_custom_button(__("Office Out(Shift)"),
							function() {
							frm.events.office_out_shift(frm, n, shift_end_time);
							}
						).toggleClass('btn-primary', !(frm.doc.employees || []).length);
					}
				}
		}
		});
		// var df = frappe.meta.get_docfield("Employee Checkin","reason", frm.doc.name);
		// frm.set_df_property("reason", "reqd", frm.doc.time_difference > 0.0);
		frm.toggle_display("reason", frm.doc.time_difference > 0.0);
	},
	lunch_out: function (frm, n, lunch_out_start) {
		return frappe.call({
			doc: frm.doc,
			method: 'lunch_out',
			args: {"time": n, "lo_start": lunch_out_start},
			callback: function(r) {
				// frm.save();
				frm.refresh_field("logs");
			}
		})
	},
	lunch_in: function (frm, n, lunch_in_start) {
		return frappe.call({
			doc: frm.doc,
			method: 'lunch_in',
			args: {"time": n, "li_start": lunch_in_start},
			callback: function(r) {
				// frm.save();
				frm.refresh_field("logs");
			}
		})
	},
	office_out: function (frm, n, office_out_start) {
		return frappe.call({
			doc: frm.doc,
			method: 'office_out',
			args: {"time": n, "oo_start": office_out_start},
			callback: function(r) {
				frm.refresh_field("logs");
			}
		})
	},
	office_out_shift: function (frm, n, shift_end_time) {
		return frappe.call({
			doc: frm.doc,
			method: 'office_out_shift',
			args: {"time": n, "se_time": shift_end_time, "shift":frm.doc.shift},
			callback: function(r) {
				// frm.save();
				frm.refresh_field("logs");
			}
		})
	},
});
