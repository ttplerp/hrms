// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('OT Update Tools', {
	onload: function(frm){
		// Your Code here
	},
	refresh: function(frm){
	// Write Your Code here
		frm.fields_dict['ot_details'].grid.get_field('employee').get_query = function(doc, cdt, cdn) {
			var child = locals[cdt][cdn];
			return {    
				filters:[
					['branch', '=', frm.doc.branch]
				]
			}
		}
		frm.fields_dict['temporary_staff_details'].grid.get_field('name_code').get_query = function(doc, cdt, cdn) {
			var child = locals[cdt][cdn];
			return {    
				filters:[
					['deployed_branch', '=', frm.doc.branch]
				]
			}
		}
		if(frm.doc.workflow_state == "Pending HR Action" && frappe.user_roles.includes("HR Manager")){
			if(frm.doc.docstatus == 1){
				frm.page.set_primary_action(__('Post OT Entries'), () => {
					post_ot_entries(frm);
				});
			} 	
		}
	},
	memo: function(frm){
		$.each(frm.doc.ot_details || [], function(i, v) {
			frappe.model.set_value(v.doctype, v.name, "remarks", frm.doc.memo);
		});
		$.each(frm.doc.temporary_staff_details || [], function(i, v) {
			frappe.model.set_value(v.doctype, v.name, "remarks", frm.doc.memo);
		});
	},
	overtime_type: function(frm) {
		$.each(frm.doc.ot_details || [], function(i, v) {
			frappe.model.set_value(v.doctype, v.name, "overtime_type", frm.doc.overtime_type);
		});
		$.each(frm.doc.temporary_staff_details || [], function(i, v) {
			frappe.model.set_value(v.doctype, v.name, "ot_type", frm.doc.overtime_type);
		});
	}
})

frappe.ui.form.on('OT tools items', {
	"refresh": function(frm, cdt, cdn){
		frm.set_query("employee", function() {
						return {
							filters:[
								['branch', '=', frm.doc.branch]
								]
						};
				});	
	},
	"employee": function(frm, cdt,cdn) {
		frappe.model.set_value(cdt, cdn, "remarks", frm.doc.memo);
		frappe.model.set_value(cdt, cdn, "overtime_type", frm.doc.overtime_type);
		get_rate_base_on_overtime_type(frm, cdt, cdn);
		calculate_time(frm, cdt, cdn);
	},
	"from_date": function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn);
	},
	"to_date": function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn);
    },
	approved_ot_hrs: function(frm, cdt, cdn){
		calculate_time(frm, cdt, cdn);
	},
	overtime_type: function(frm, cdt, cdn){
		get_rate_base_on_overtime_type(frm, cdt, cdn);
		calculate_time(frm, cdt, cdn);
	}
})

var post_ot_entries = function(frm){
	frappe.call({
		method: "post_overtime_entries",
		doc: frm.doc,
		callback: function(r){
			cur_frm.refresh();
		},
		freeze: true,
		freeze_message: "Posting Entries to Overtime Application.... Please Wait",
	});
	//window.location.reload();
}

function get_rate_base_on_overtime_type(frm, cdt, cdn){
	var i = locals[cdt][cdn]
	frappe.call({
		method: "hrms.hr.doctype.ot_update_tools.ot_update_tools.get_rate",
		args: {
				employee: i.employee,
				overtime_type: i.overtime_type,
			},
		callback: function(r){
			//r.message[0] - overtime_normal_rate
			//r.message[1] - sunday_overtime_half_day
			//r.message[2] - ","sunday_overtime_full_day
			frappe.model.set_value(cdt, cdn, "ot_rate", r.message[0]);
			frappe.model.set_value(cdt, cdn, "ot_rate_half_day", r.message[1]);
			frappe.model.set_value(cdt, cdn, "ot_rate_full_day", r.message[2]);
			frm.refresh_fields();
		}
	})	
}

function calculate_time(frm, cdt, cdn) {
	var item = locals[cdt][cdn];
	var total_amount = 0;
	var temp_total_amount = 0;
	// var total_time = 0;
	if(item.overtime_type == "Sunday Overtime (Half Day)"){
		frappe.model.set_value(cdt, cdn, "number_of_hours", 4);
		frappe.model.set_value(cdt, cdn, "approved_ot_hrs", 4);
		frappe.model.set_value(cdt, cdn, "ot_amount", flt(item.ot_rate_half_day))
	}
	else if(item.overtime_type == "Sunday Overtime (Full Day)"){
		frappe.model.set_value(cdt, cdn, "number_of_hours", 8);
		frappe.model.set_value(cdt, cdn, "approved_ot_hrs", 8);
		frappe.model.set_value(cdt, cdn, "ot_amount", flt(item.ot_rate_full_day))
	}else if(item.to_date && item.from_date) {
			const from_date = new Date('2024-05-11'+' '+ item.from_date);
			const to_date = new Date('2024-05-11'+' '+ item.to_date);
			var hours = moment(to_date).diff(moment(from_date), "seconds") / 3600;
			frappe.model.set_value(cdt, cdn, "number_of_hours", hours);
			frappe.model.set_value(cdt, cdn, "ot_amount", flt(item.ot_rate * item.approved_ot_hrs))
	}else{
		frappe.model.set_value(cdt, cdn, "number_of_hours", 0);
	}
	
	frm.doc.ot_details.forEach(function(item) {
		if(item.ot_amount) {
			total_amount += item.ot_amount
		}	
	})
	frm.doc.temporary_staff_details.forEach(function(item) {
		if(item.temp_ot_amount) {
			temp_total_amount += item.temp_ot_amount
		}	
	})
	frm.set_value("total_amount", total_amount+temp_total_amount);
	cur_frm.refresh_field("total_amount");
}

frappe.ui.form.on('Temporary staff items', {
	"refresh": function(frm,cdt,cdn) {
		frm.set_query("name_code", function() {
			return {
				filters:[
					['deployed_branch', '=', frm.doc.branch]
					]
			};
		});	
	},
	"name_code": function(frm, cdt,cdn) {
		frappe.model.set_value(cdt, cdn, "remarks", frm.doc.memo);
		frappe.model.set_value(cdt, cdn, "ot_type", frm.doc.overtime_type);
		get_temp_overtime_rate(frm, cdt, cdn);
		calculate_ot(frm, cdt, cdn);
	},
	"ot_hours": function(frm, cdt, cdn) {
		calculate_ot(frm,cdt, cdn);
	},
	"approved_ot_hours": function(frm, cdt, cdn){
		calculate_ot(frm, cdt, cdn);
	},
	"ot_type": function(frm, cdt, cdn){
		get_temp_overtime_rate(frm, cdt, cdn);
		calculate_ot(frm, cdt, cdn);
	}
})

function get_temp_overtime_rate(frm, cdt, cdn){
	var i = locals[cdt][cdn]
	frappe.call({
		method: "hrms.hr.doctype.ot_update_tools.ot_update_tools.get_temp_overtime_rate",
		args: {
				staff: i.name_code
			},
		callback: function(r){
			console.log(r.message)
			frappe.model.set_value(cdt, cdn, "rates", r.message[0]);
			frappe.model.set_value(cdt, cdn, "half_day", r.message[1]);
			frappe.model.set_value(cdt, cdn, "full_day", r.message[2]);
			frm.refresh_fields();
		}
	})	
}

function calculate_ot(frm, cdt, cdn){
	var item = locals[cdt][cdn];
	var total_amount = 0;
	var temp_total_amount = 0;
	// var total_time = 0;
	if(item.overtime_type == "Sunday Overtime (Half Day)"){
		frappe.model.set_value(cdt, cdn, "ot_hours", 4);
		frappe.model.set_value(cdt, cdn, "approved_ot_hours", 4);
		frappe.model.set_value(cdt, cdn, "temp_ot_amount", flt(item.half_day))
	}
	else if(item.overtime_type == "Sunday Overtime (Full Day)"){
		frappe.model.set_value(cdt, cdn, "ot_hours", 8);
		frappe.model.set_value(cdt, cdn, "approved_ot_hours", 8);
		frappe.model.set_value(cdt, cdn, "temp_ot_amount", flt(item.full_day))
	}else{
		/*
		const from_date = new Date('2024-05-11'+' '+ item.from_date);
		const to_date = new Date('2024-05-11'+' '+ item.to_date);
		var hours = moment(to_date).diff(moment(from_date), "seconds") / 3600;
		frappe.model.set_value(cdt, cdn, "approved_ot_hours", hours);
		*/
		if(item.approved_ot_hours){
			frappe.model.set_value(cdt, cdn, "temp_ot_amount", flt(item.rates * item.approved_ot_hours));
		}
	}
	
	frm.doc.temporary_staff_details.forEach(function(item) {
		if(item.temp_ot_amount) {
			temp_total_amount += item.temp_ot_amount
		}	
	})
	frm.doc.ot_details.forEach(function(item) {
		if(item.ot_amount) {
			total_amount += item.ot_amount
		}	
	})
	frm.set_value("total_amount", total_amount+temp_total_amount);
	cur_frm.refresh_field("total_amount");
}

