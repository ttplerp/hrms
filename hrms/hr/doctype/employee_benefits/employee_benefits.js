// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Benefits', {
	refresh: function(frm) {
		if(frm.doc.employee_separation_id){
			frm.set_value("purpose","Separation")
		}
		else if(frm.doc.employee_transfer_id){
			frm.set_value("purpose","Transfer")
		}
		if(frm.doc.docstatus == 1 && frm.doc.journal){
			frm.add_custom_button(__('Bank Entries'), function() {
				frappe.route_options = {
					"Journal Entry Account.reference_type": me.frm.doc.doctype,
					"Journal Entry Account.reference_name": me.frm.doc.name,
				};
				frappe.set_route("List", "Journal Entry");
			}, __("View"));
		}


		if(!frm.doc.__islocal && frm.doc.workflow_state != "Draft"){
			frm.set_df_property("purpose", "read_only", 1);
		}

		frm.set_df_property("separation_date","hidden",frm.doc.purpose!="Separation" && frm.doc.purpose!="Transfer");
		frm.set_df_property("separation_date","reqd",frm.doc.purpose=="Separation");
		frm.refresh_fields();

	},
	onload: function(frm) {
		if(!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today())
		}
	},
	"total_amount": function(frm) {
				var total_amount = 0;
				for (var i in frm.doc.items) {
					var item = frm.doc.items[i];
					total_amount += item.amount;
				}
				console.log("testing..." + total_amount);
				frm.set_value("total_amount",total_amount);
		        },
	purpose: function(frm){
		frm.set_df_property("separation_date","hidden",frm.doc.purpose!="Separation" && frm.doc.purpose!="Transfer");
		frm.set_df_property("separation_date","reqd",frm.doc.purpose=="Separation" || frm.doc.purpose=="Transfer");
		frm.refresh_fields();	
	}
		
});

frappe.ui.form.on("Separation Item", {
	form_render: function (frm, cdt, cdn) {
		var item = locals[cdt][cdn];
		var terrain_rate = frappe.meta.get_docfield("Separation Item", "terrain_rate", frm.doc.name);
		var distance = frappe.meta.get_docfield("Separation Item", "distance", frm.doc.name);
		var load_capacity = frappe.meta.get_docfield("Separation Item", "load_capacity", frm.doc.name);
	},
    "benefit_type": function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "amount", null);
		frappe.model.set_value(cdt, cdn, "earned_leave_balance", null);
		frappe.model.set_value(cdt, cdn, "distance", null);
		frappe.model.set_value(cdt, cdn, "terrain_rate", null);
		frappe.model.set_value(cdt, cdn, "load_capacity", null);
		if(frm.doc.purpose != "Separation" && frm.doc.purpose != "Upgradation"){
			if(row.benefit_type == "Provision for Leave Encashment"){
				frappe.model.set_value(cdt, cdn, "amount", null);
				frappe.model.set_value(cdt, cdn, "earned_leave_balance", null);
				frappe.model.set_value(cdt, cdn, "benefit_type", null);
				frm.refresh_fields();
				frappe.throw("Leave Encashment cannot be claimed for Transfer.")
			}
			if(row.benefit_type == "Provision for Employee Gratuity Fund"){
				frappe.model.set_value(cdt, cdn, "amount", null);
				frappe.model.set_value(cdt, cdn, "benefit_type", null);
				frm.refresh_fields();
				frappe.throw("Gratuity cannot be claimed for Transfer.")
			}
		}
		if(row.benefit_type != "Carriage Charges" || row.benefit_type != "Provision for Carriage Charges"){
			frappe.model.set_value(cdt, cdn, "distance", null);
			frappe.model.set_value(cdt, cdn, "terrain_rate", null);
			frappe.model.set_value(cdt, cdn, "load_capacity", null);
		}
		else if(row.benefit_type != "Provision for Leave Encashment"){
			frappe.model.set_value(cdt, cdn, "earned_leave_balance", null);
		}
    	var item = locals[cdt][cdn]
		if(item.benefit_type == "Transfer Grant" || item.benefit_type == "Provision for Travel Allowance" || item.benefit_type == "Provision for Transfer Grant"){
			return frappe.call({
				method: "hrms.hr.doctype.employee_benefits.employee_benefits.get_basic_salary",
				args: {"employee": frm.doc.employee},
				callback: function(r) {
					console.log(r.message);
					if(r.message) {
						frappe.model.set_value(cdt, cdn,"amount", r.message);
					}
					frm.refresh_fields()
				}
			});
		}
		else if(item.benefit_type == "Provision for Employee Gratuity Fund"){
			return frappe.call({
				method: "hrms.hr.doctype.employee_benefits.employee_benefits.get_gratuity_amount",
				args: {"employee": frm.doc.employee},
				callback: function(r) {
					console.log(r.message);
					if(r.message) {
						frappe.model.set_value(cdt, cdn,"amount", r.message);
					}
					frm.refresh_fields()
				}
			});
		}
		else if (item.benefit_type == "Provision for Leave Encashment"){
			if(frm.doc.purpose == "Separation"){
				if(frm.doc.separation_date && frm.doc.employee){
					return frappe.call({
						method: "hrms.hr.doctype.employee_benefits.employee_benefits.get_leave_encashment_amount",
						args: {"employee": frm.doc.employee, "date":frm.doc.separation_date},
						callback: function(r) {
							console.log(r.message);
							if(r.message) {
								frappe.model.set_value(cdt, cdn,"amount", r.message[0]);
								frappe.model.set_value(cdt, cdn,"earned_leave_balance", r.message[1]);
								frappe.model.set_value(cdt, cdn,"tax_amount", r.message[2]);
							}
							frm.refresh_fields()
						}
					});
				}
				else{
					// frappe.msgprint("Employee and Separation Date fields cannot be blank")
				}
			}
			else if(frm.doc.purpose == "Upgradation"){
				if(frm.doc.posting_date && frm.doc.employee){
					return frappe.call({
						method: "hrms.hr.doctype.employee_benefits.employee_benefits.get_leave_encashment_amount",
						args: {"employee": frm.doc.employee, "date":frm.doc.posting_date},
						callback: function(r) {
							console.log(r.message);
							if(r.message) {
								frappe.model.set_value(cdt, cdn,"amount", r.message[0]);
								frappe.model.set_value(cdt, cdn,"earned_leave_balance", r.message[1]);
								frappe.model.set_value(cdt, cdn,"tax_amount", r.message[2]);
							}
							frm.refresh_fields()
						}
					});
				}
			}

		}
		else if(item.benefit_type == "Carriage Charges" || item.benefit_type == "Provision for Carriage Charges"){
			if(item.terrain_rate && item.distance != 0 && item.load_capacity){
				frappe.model.set_value(cdt, cdn, "amount",flt(item.terrain_rate)*flt(item.distance)*flt(item.load_capacity))
			}
		}
	},

	"distance": function(frm, cdt, cdn){
		var item = locals[cdt][cdn];
		if(item.benefit_type == "Carriage Charges" || item.benefit_type == "Provision for Carriage Charges"){
			if(item.terrain_rate && item.distance != 0 && item.load_capacity){
				frappe.model.set_value(cdt, cdn, "amount",flt(item.terrain_rate)*flt(item.distance)*flt(item.load_capacity))
			}
		}
		else{
			frappe.model.set_value(cdt, cdn, "distance", null);
			frappe.model.set_value(cdt, cdn, "terrain_rate", null);
			frappe.model.set_value(cdt, cdn, "load_capacity", null);
		}
	},

	"terrain_rate": function(frm, cdt, cdn){
		var item = locals[cdt][cdn];
		if(item.benefit_type == "Carriage Charges" || item.benefit_type == "Provision for Carriage Charges"){
			if(item.terrain_rate && item.distance != 0 && item.load_capacity){
				frappe.model.set_value(cdt, cdn, "amount",flt(item.terrain_rate)*flt(item.distance)*flt(item.load_capacity))
			}
			// else{
			// 	frappe.throw("For calculation of carriage charges Terrain Rate, Distance and Load Capacity are mandatory")
			// }
		}
		else{
			frappe.model.set_value(cdt, cdn, "distance", null);
			frappe.model.set_value(cdt, cdn, "terrain_rate", null);
			frappe.model.set_value(cdt, cdn, "load_capacity", null);
		}
	},

	"load_capacity": function(frm, cdt, cdn){
		var item = locals[cdt][cdn];
		if(item.benefit_type == "Carriage Charges" || item.benefit_type == "Provision for Carriage Charges"){
			if(item.terrain_rate && item.distance != 0 && item.load_capacity){
				frappe.model.set_value(cdt, cdn, "amount",flt(item.terrain_rate)*flt(item.distance)*flt(item.load_capacity))
			}
			// else{
			// 	frappe.throw("For calculation of carriage charges Terrain Rate, Distance and Load Capacity are mandatory")
			// }
		}
		else{
			frappe.model.set_value(cdt, cdn, "distance", null);
			frappe.model.set_value(cdt, cdn, "terrain_rate", null);
			frappe.model.set_value(cdt, cdn, "load_capacity", null);
		}
	},

	"amount": function(frm, cdt, cdn) {
		set_tax_amount(frm, cdt, cdn);
	},

	"payable_amount": function(frm,cdt,cdn){
		set_total(frm);
	},

	items_remove: function(frm, cdt, cdn){
		set_total(frm);
	}
});

frappe.ui.form.on("Deduction Details", {
	"deduction_type": function(frm, cdt, cdn){
		get_outstanding_amount(frm, cdt, cdn);
	},

	"amount": function(frm, cdt, cdn){
		set_total(frm);
	},

	deduction_details_remove: function(frm, cdt, cdn){
		set_total(frm);
	}
});

var get_outstanding_amount = function(frm, cdt, cdn){
	let row = locals[cdt][cdn];
}

var set_tax_amount = function(frm, cdt, cdn){
	var row = locals[cdt][cdn];
	if(row.benefit_type == "Provision for Leave Encashment"){
		frappe.call({
			"method": "hrms.hr.doctype.employee_benefits.employee_benefits.get_leave_encashment_tax",
			"args": {
				amount: row.amount,
				benefit_type: row.benefit_type
			},
			callback: function(r){
				let tax_amount = r.message ? flt(r.message) : 0;
				frappe.model.set_value(cdt, cdn, "tax_amount", flt(tax_amount,2));
				frappe.model.set_value(cdt, cdn, "payable_amount", flt(row.amount,2) - flt(tax_amount,2));
			}
		})
	} else {
		frappe.model.set_value(cdt, cdn, "tax_amount", 0);
		frappe.model.set_value(cdt, cdn, "payable_amount", flt(row.amount,2));
	}
}

var set_total = function(frm){
	var earnings = frm.doc.items || [];
	var deductions = frm.doc.deduction_details || [];
	var total_earning = 0, total_deduction = 0, net_amount = 0;

	earnings.forEach(function(rec, i){
		total_earning += flt(rec.amount);
		total_deduction += flt(rec.tax_amount);
	})

	deductions.forEach(function(rec, i){
		total_deduction += flt(rec.amount);
	})

	frm.set_value("total_amount", flt(total_earning));
	frm.set_value("total_deducted_amount", flt(total_deduction));
	frm.set_value("net_amount", flt(total_earning)-flt(total_deduction));
}
