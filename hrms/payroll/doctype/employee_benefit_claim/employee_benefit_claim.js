// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Benefit Claim', {
	refresh: function(frm) {
		if(frm.doc.employee_separation_id){
			cur_frm.set_value("purpose","Separation")
		}
		else if(frm.doc.employee_transfer_id){
			cur_frm.set_value("purpose","Transfer")
		}
		if(frm.doc.docstatus == 1 && frm.doc.journal){
			cur_frm.add_custom_button(__('Bank Entries'), function() {
				frappe.route_options = {
					"Journal Entry Account.reference_type": me.frm.doc.doctype,
					"Journal Entry Account.reference_name": me.frm.doc.name,
				};
				frappe.set_route("List", "Journal Entry");
			}, __("View"));
		}
		
		if(frm.doc.workflow_state == "Draft" || frm.doc.workflow_state == "Rejected"){
                        frm.set_df_property("benefit_approver", "hidden", 1);
                        frm.set_df_property("benefit_approver_name", "hidden",1);
                }

		if(!frm.doc.__islocal && frm.doc.workflow_state != "Draft"){
			console.log("testing : purpose:" + frm.doc.workflow_state);
                        frm.set_df_property("purpose", "read_only", 1);
		}

	},
	"employee": function(frm){
		cur_frm.clear_table("items");
		cur_frm.clear_table("deduction_details");
		populate_deduction_details(frm);
		cur_frm.refresh_fields();
	},
	onload: function(frm) {
		if(!frm.doc.posting_date) {
			cur_frm.set_value("posting_date", get_today())
		}
	},
	// "total_amount": function(frm) {
	// 			var total_amount = 0;
	// 			for (var i in cur_frm.doc.items) {
	// 				var item = cur_frm.doc.items[i];
	// 				total_amount += item.amount;
	// 			}
	// 			console.log("testing..." + total_amount);
	// 			frm.set_value("total_amount",total_amount);
	// 	        },
	// purpose: function(frm){
	// 	frm.set_df_property("separation_date","hidden",frm.doc.purpose!="Separation" && frm.doc.purpose!="Transfer");
	// 	frm.set_df_property("separation_date","reqd",frm.doc.purpose=="Separation" || frm.doc.purpose=="Transfer");
	// 	frm.refresh_fields();	
	// }
});

frappe.ui.form.on("Separation Item", {
    "benefit_type": function(frm, cdt, cdn) {
		let item = locals[cdt][cdn];

		reset_benefit_record(frm, cdt, cdn);
		if (item.benefit_type == "Balance EL reimbursement"){
			set_earned_leave_balance(frm, cdt, cdn);
		}
		else if (item.benefit_type == "Pay" || item.benefit_type == "Transfer Grant" || item.benefit_type == "Travelling Allowance"){
			set_basic_pay(frm, cdt, cdn);
		}
		if(item.benefit_type != "Carriage Charges"){
			frappe.model.set_value(cdt, cdn, "distance", null);
			frappe.model.set_value(cdt, cdn, "terrain_rate", null);
			frappe.model.set_value(cdt, cdn, "load_capacity", null);
		}
		if(frm.doc.purpose != "Separation" && frm.doc.purpose != "Upgradation"){
			if(item.benefit_type == "Leave Encashment"){
				frappe.model.set_value(cdt, cdn, "amount", null);
				frappe.model.set_value(cdt, cdn, "earned_leave_balance", null);
				frappe.model.set_value(cdt, cdn, "benefit_type", null);
				frm.refresh_fields();
				frappe.throw("Leave Encashment cannot be claimed for Transfer.")
			}
			if(item.benefit_type == "Gratuity"){
				frappe.model.set_value(cdt, cdn, "amount", null);
				frappe.model.set_value(cdt, cdn, "benefit_type", null);
				frm.refresh_fields();
				frappe.throw("Gratuity cannot be claimed for Transfer.")
			}
		}
		if(item.benefit_type == "Gratuity"){
			return frappe.call({
				method: "get_gratuity_amount",
				doc: frm.doc,
				args: {"employee": frm.doc.employee},
				callback: function(r) {
					console.log(r.message);
					if(r.message) {
						frappe.model.set_value(cdt, cdn,"amount", r.message);
					}
					cur_frm.refresh_fields()
				}
			});
		}
		else if (item.benefit_type == "Leave Encashment"){
			if(frm.doc.purpose == "Separation"){
				if(frm.doc.separation_date && frm.doc.employee){
					return frappe.call({
						method: "get_leave_encashment_amount",
						doc: frm.doc,
						args: {"employee": frm.doc.employee, "date":frm.doc.separation_date},
						callback: function(r) {
							console.log(r.message);
							if(r.message) {
								frappe.model.set_value(cdt, cdn,"amount", r.message[0]);
								frappe.model.set_value(cdt, cdn,"earned_leave_balance", r.message[1]);
								frappe.model.set_value(cdt, cdn,"tax_amount", r.message[2]);
							}
							cur_frm.refresh_fields()
						}
					});
				}
				else{
					// frappe.msgprint("Employee and Separation Date fields cannot be blank")
				}
			}

		}
		// if(item.benefit_type == "Carriage Charges"){
		// 	if(item.terrain_rate && item.distance != 0 && item.load_capacity){
		// 		console.log("here")
		// 		frappe.model.set_value(cdt, cdn, "amount",flt(item.terrain_rate)*flt(item.distance)*flt(item.load_capacity))
		// 	}
		// 	// else{
		// 	// 	frappe.throw("For calculation of carriage charges Terrain Rate, Distance and Load Capacity are mandatory")
		// 	// }
		// }
		if(item.benefit_type != "Leave Encashment"){
			frappe.model.set_value(cdt, cdn, "earned_leave_balance", null);
		}
		frm.refresh_fields();
	},

	"earned_leave_balance": function(frm, cdt, cdn){
		set_el_reimbursement(frm, cdt, cdn);
	},

	"amount": function(frm, cdt, cdn) {
		set_tax_amount(frm, cdt, cdn);
	},

	"net_amount": function(frm, cdt, cdn){
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


var populate_deduction_details = function(frm){
	return frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Employee Deduction Type",
			order_by: "name",
			fields: ["name"],
		},
		callback: function(r){
			console.log(r.message)
			if(r.message){
				r.message.forEach(function(rec){
					var child = cur_frm.add_child("deduction_details");
					frappe.model.set_value(child.doctype, child.name, "deduction_type", rec.name);
					cur_frm.refresh_field("deduction_details");
				});
			}
		}
	});
}

var reset_benefit_record = function(frm, cdt, cdn){
	frappe.model.set_value(cdt, cdn,"actual_amount", null);
	frappe.model.set_value(cdt, cdn,"amount", 0);
	frappe.model.set_value(cdt, cdn,"earned_leave_balance", null);
	frappe.model.set_value(cdt, cdn,"actual_earned_leave_balance", null);
	frappe.model.set_value(cdt, cdn,"tax_amount", 0);
	frappe.model.set_value(cdt, cdn,"net_amount", 0);
}

// var set_transfer_grant = function(frm, cdt, cdn){
// 	return frappe.call({
// 		method: "get_transfer_grant",
// 		args: {"employee": frm.doc.employee},
// 		callback: function(r) {
// 			if(r.message) {
// 				frappe.model.set_value(cdt, cdn,"actual_amount", flt(r.message,2));
// 				frappe.model.set_value(cdt, cdn,"amount", flt(r.message,2));
// 				frappe.model.set_value(cdt, cdn,"earned_leave_balance", null);
// 				frappe.model.set_value(cdt, cdn,"actual_earned_leave_balance", null);
// 				frappe.model.set_value(cdt, cdn,"tax_amount", 0);
// 				frappe.model.set_value(cdt, cdn,"net_amount", flt(r.message,2));
// 			}
// 			cur_frm.refresh_fields()
// 		}
// 	});
// }

var set_earned_leave_balance = function(frm, cdt, cdn){
	if(frm.doc.purpose == "Separation" && frm.doc.separation_date && frm.doc.employee){
		return frappe.call({
			method: "hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on",
			args: {
				employee: frm.doc.employee, 
				leave_type: "Earned Leave",
				date: frm.doc.separation_date},
			callback: function(r) {
				if(r.message) {
					frappe.model.set_value(cdt, cdn,"actual_earned_leave_balance", flt(r.message));
					frappe.model.set_value(cdt, cdn,"earned_leave_balance", flt(r.message));
				}
				cur_frm.refresh_fields()
			}
		});
	}
}
var set_basic_pay = function(frm, cdt, cdn){
	var item = locals[cdt][cdn];
	if((frm.doc.purpose == "Separation" || frm.doc.purpose == "Transfer")&& frm.doc.employee){
		return frappe.call({
			method: "get_basic_pay",
			doc: frm.doc,
			args: {"employee": frm.doc.employee}, 
			callback: function(r) {
				if(r.message) {
					frappe.model.set_value(cdt, cdn,"amount", flt(r.message[0]));
					console.log(item.apply_tax)
					if(item.apply_tax==1){
						frappe.model.set_value(cdt, cdn,"tax_amount", flt(r.message[1]));
						frappe.model.set_value(cdt, cdn,"net_amount", flt(r.message[0]-r.message[1]));
					}
					else{
						frappe.model.set_value(cdt, cdn,"net_amount", flt(r.message[0]));
						frappe.model.set_value(cdt, cdn,"tax_amount", 0);
					}
				}
				cur_frm.refresh_fields()
			}
		});
		
	}
}
var set_el_reimbursement = function(frm, cdt, cdn){
	let row = locals[cdt][cdn];
	if(flt(row.earned_leave_balance) > 0){
		frappe.call({
			method: "get_basic_pay",
			args: {"employee": frm.doc.employee},
			callback: function(r) {
				let basic_pay = 0, amount = 0;
				basic_pay = r.message ? flt(r.message) : 0;
				amount = (flt(basic_pay)/30.0)*flt(row.earned_leave_balance);

				frappe.model.set_value(cdt, cdn,"actual_amount", flt(amount,2));
				frappe.model.set_value(cdt, cdn,"amount", flt(amount,2));
				cur_frm.refresh_fields()
			}
		});
	} else {
		frappe.model.set_value(cdt, cdn,"actual_amount", null);
		frappe.model.set_value(cdt, cdn,"amount", 0);
	}
}

var set_tax_amount = function(frm, cdt, cdn){
	let row = locals[cdt][cdn];
	if(flt(row.amount) > 0){
		if(row.apply_tax == 1){
			frappe.call({
				method: "hrms.hr.hr_custom_functions.get_salary_tax",
				args: {
					gross_amt: flt(row.amount)
				},
				callback: function(r){
					let tax_amount = r.message ? flt(r.message) : 0;
					frappe.model.set_value(cdt, cdn,"tax_amount", flt(tax_amount,2));
					frappe.model.set_value(cdt, cdn,"net_amount", flt(row.amount,2) - flt(tax_amount,2));
				}
			});
		} else {
			frappe.model.set_value(cdt, cdn,"tax_amount", null);
			frappe.model.set_value(cdt, cdn,"net_amount", flt(row.amount,2));
		}
	} else {
		reset_benefit_record(frm, cdt, cdn);
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
	// frm.set_value("total_deducted_amount", flt(total_deduction));
	// frm.set_value("net_amount", flt(total_earning)-flt(total_deduction));
}

var get_outstanding_amount = function(frm, cdt, cdn){
	let row = locals[cdt][cdn];
	if(["Salary Advance Deduction", "Festival Advance Deduction"].includes(row.deduction_type)){
		if(frm.doc.employee && row.deduction_type){
			return frappe.call({
				method: "get_outstanding_amount",
				args: {
					employee: frm.doc.employee,
					salary_component: row.deduction_type 
				},
				callback: function(r){
					frappe.model.set_value(cdt, cdn, "amount", flt(r.message[0]));
					frappe.model.set_value(cdt, cdn, "salary_structure_id", r.message[1]);
					frappe.model.set_value(cdt, cdn, "reference_id", r.message[2]);
				}
			});
		}
	}
}
