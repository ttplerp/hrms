// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("employee", "designation", "designation")
cur_frm.add_fetch("employee", "grade", "grade")

frappe.ui.form.on('Travel Request', {
	refresh: function(frm){
		if (frm.doc.docstatus === 0 && !frm.doc.__islocal && cint(frm.doc.need_advance) == 1) {
			cur_frm.add_custom_button('Request Advance', function() {
				return frappe.call({
					method: "make_advance_payment",
					doc:frm.doc,
					callback: function(r) {
						var doclist = frappe.model.sync(r.message);
						frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
					}
				});
			});
		}
		// if (frm.doc.workflow_state == 'Draft') {
		// 	frm.add_custom_button(__('Notify Employee'), function(){
		// 		return frappe.call({
		// 			method:"notify_supervisor",
		// 			doc: frm.doc,
		// 			callback: function (){
		// 				frm.refresh_field("notify")
		// 			}
		// 		});
		// 	}, ("Notify"));
		// }
	},
	onload: function(frm) {
		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", frappe.datetime.get_today());
		}
	},
	"need_advance": function(frm) {
		if(frm.doc.need_advance != 1){
			frm.set_value("advance_amount", 0);
		}else{
			frm.toggle_reqd("estimated_amount", frm.doc.need_advance==1);
			frm.toggle_reqd("currency", frm.doc.need_advance==1);
			frm.toggle_reqd("advance_amount", frm.doc.need_advance==1);
		}
	},
	"advance_amount": function(frm) {
		if(frm.doc.advance_amount > frm.doc.total_travel_amount * 0.9) {
			msgprint("Advance amount cannot be greater than 90% of the <b>Total Travel Amount</b>")
			frm.set_value("advance_amount", 0)
		}
		else {
			if(frm.doc.currency == "BTN") {
				frm.set_value("advance_amount_nu", flt(frm.doc.advance_amount))
			}
			else {
				update_advance_amount(frm)
			}
		}
	},
	"currency": function(frm) {
		if(frm.doc.advance_amount != 0 && frm.doc.currency != 'BTN'){
			update_advance_amount(frm)
		}
	},
});

frappe.ui.form.on("Travel Itinerary", {
	form_render: function(frm, cdt, cdn){
		var item = locals[cdt][cdn];
		if(item.dsa <= 0){
			var dsa_per_day = frm.doc.dsa_per_day;
			frappe.model.set_value(cdt, cdn, "dsa", dsa_per_day);
		}
	},	
	"from_date": function(frm, cdt, cdn) {
		set_noof_days(frm, cdt, cdn);
	},
		
	"to_date": function(frm, cdt, cdn) {
		set_noof_days(frm, cdt, cdn);
	},
	
	"halt": function(frm, cdt, cdn) {
		var item = locals[cdt][cdn]
		cur_frm.toggle_reqd("to_date", item.halt);
	},
	"distance": function(frm, cdt, cdn){
		update_amount(frm, cdt, cdn);
	},
	"mileage_rate": function(frm, cdt, cdn){
		update_amount(frm, cdt, cdn);
	},
	"amount": function(frm, cdt,cdn){
		update_total(frm,cdt, cdn);
	},
	"mileage_amount": function(frm, cdt,cdn){
		update_total(frm,cdt, cdn);
	},
	"fare_amount": function(frm, cdt,cdn){
		update_total(frm,cdt, cdn);
	},
	"entertainment_amount": function(frm, cdt,cdn){
		update_total(frm,cdt, cdn);
	},
	"hotel_charges_amount": function(frm, cdt,cdn){
		update_total(frm,cdt, cdn);
	},
	"passport_fees": function(frm, cdt,cdn){
		update_total_claim(cdt, cdn);
		update_total(frm,cdt, cdn);
	},
	"visa_fees": function(frm, cdt,cdn){
		update_total(frm,cdt, cdn);
	},
	"incidental_fees": function(frm, cdt,cdn){
		update_total(frm,cdt, cdn);
	},
	"dsa": function(frm, cdt, cdn){
        let row = locals[cdt][cdn]
		update_total_claim(cdt, cdn)
	},
	"dsa_percent": function(frm, cdt, cdn){
        let row = locals[cdt][cdn]
		update_total_claim(cdt, cdn)
	},
	"currency": function(frm, cdt,cdn){
        let row = locals[cdt][cdn]
		update_total_claim(cdt, cdn)
	},
	"passport_fees_currency": function (frm, cdt, cdn) {
		update_total_claim(cdt, cdn)
	},
	"currency_exchange_date": function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.currency_exchange_date){
			update_total_claim(cdt, cdn)
		}
		update_total(frm, cdt, cdn)
	},
	"visa_fees_currency": function (frm, cdt, cdn) {
		update_total_claim(cdt, cdn)
	},
	"incidental_fees_currency": function (frm, cdt, cdn) {
		update_total_claim(cdt, cdn)
	},
	"porter_pony_charges": function (frm, cdt, cdn) {
		update_total_claim(cdt, cdn)
	},
	"visa_fees": function (frm, cdt, cdn) {
		update_total_claim(cdt, cdn)
	},
	"passport_fees": function (frm, cdt, cdn) {
		update_total_claim(cdt, cdn)
	},
	"incidental_fees": function (frm, cdt, cdn) {
		update_total_claim(cdt, cdn)
	},
	"no_days_actual":function(frm, cdt,cdn){
		update_amount(frm,cdt, cdn);
	}

}); 

var update_total = function(frm,cdt, cdn){
	var item = locals[cdt][cdn];
	var total=0;
	total = flt(item.amount)+flt(item.mileage_amount)+flt(item.fare_amount)+flt(item.entertainment_amount)+flt(item.hotel_charges_amount)+flt(item.visa_fees_exchange_rate*item.visa_fees,2)+flt(item.passport_fees_exchange_rate*item.passport_fees,2)+flt(item.incidental_expenses_exchange_rate*item.incidental_fees,2);
	if(frm.doc.travel_type != "International"){
		total = total + flt(item.porter_pony_charges)
	}
	frappe.model.set_value(cdt, cdn, "total_claim", flt(total));
	frappe.model.set_value(cdt, cdn, "actual_amount", flt(total));
}

var update_amount = function(frm, cdt, cdn){
	var item = locals[cdt][cdn];
	var dsa_amount = 0, mileage_amount = 0;

	// if(flt(item.dsa) > 0){
	// 	dsa_amount = flt(item.no_days_actual) * (flt(item.dsa) * (flt(item.dsa_percent)/100));
	// 	frappe.model.set_value(cdt, cdn, "amount", flt(dsa_amount));
	// }

	if(item.distance > 0){
		mileage_amount = flt(item.mileage_rate) * flt(item.distance);
		frappe.model.set_value(cdt, cdn, "mileage_amount", mileage_amount);
	}else{
		return
	}

}

var set_noof_days = function(frm, cdt, cdn){
	var item = locals[cdt][cdn];
	var noof_days = 0;

	if(!item.halt && item.from_date != item.to_date){
		frappe.model.set_value(cdt, cdn, "to_date", item.from_date);
		return
	}

	if(item.from_date && item.to_date){
		if (item.to_date < item.from_date){
			msgprint("To Date cannot be earlier to From Date");
			noof_days = 0;
		} else {
			noof_days = frappe.datetime.get_day_diff(item.to_date, item.from_date) + 1;
		}
	} else {
		noof_days = 0;
	}

	frappe.model.set_value(cdt, cdn, "no_days_actual", noof_days);
}

function update_total_claim(cdt, cdn){
	var item = locals[cdt][cdn];
	item.amount = 0;
	var amount = 0;
	if(!item.currency_exchange_date){
		item.currency_exchange_date = cur_frm.doc.posting_date;
	}
	frappe.call({
		method: "hrms.hr.doctype.travel_request.travel_request.get_exchange_rate",
		args: {
			"from_currency": item.currency,
			"to_currency": "BTN",
			"posting_date":item.currency_exchange_date

		},
		callback: function(r) {
			if(r.message) {
				frappe.model.set_value(cdt, cdn, "exchange_rate", flt(r.message))
				frappe.model.set_value(cdt, cdn, "amount", flt(r.message)*flt(item.dsa) * (flt(item.dsa_percent)/100) * flt(item.no_days_actual))
				// frappe.model.set_value(cdt, cdn, "actual_amount", flt(r.message) * (flt(item.amount)))
				// amount = item.actual_amount
                cur_frm.refresh_field("itinerary")
			}
		}
	})
	//If there is visa fee
	if(item.visa_fees_currency != "BTN"){
		frappe.call({
			method: "erpnext.hr.doctype.travel_authorization.travel_authorization.get_exchange_rate",
			args: {
				"from_currency": item.visa_fees_currency,
				"to_currency": "BTN",
				"posting_date": item.currency_exchange_date
			},
			async: false,
			callback: function(vf){
				if(vf.message){
					// frappe.model.set_value(cdt, cdn, "actual_amount", flt(vf.message)*flt(item.visa_fees) + flt(amount))	
					// frappe.model.set_value(cdt, cdn, "amount", flt(vf.message)*flt(item.visa_fees) + flt(amount))
					if(item.visa_fees_currency != "BTN"){
						frappe.model.set_value(cdt, cdn, "visa_fees_exchange_rate", vf.message);
					}
					// amount = flt(vf.message)*flt(item.visa_fees) + flt(amount);
				}

			}
		})
	}
	else {
		// frappe.model.set_value(cdt, cdn, "actual_amount", flt(item.visa_fees) + flt(amount))
		// frappe.model.set_value(cdt, cdn, "amount", flt(item.visa_fees) + flt(amount))
		frappe.model.set_value(cdt, cdn, "visa_fees_exchange_rate", 1);
		// amount = flt(item.visa_fees) + flt(amount)
	}
	//If there is passport fee
	if(item.passport_fees_currency != "BTN"){
		console.log(item.passport_fees_currency)
		frappe.call({
			method: "hrms.hr.doctype.travel_request.travel_request.get_exchange_rate",
			args: {
				"from_currency": item.passport_fees_currency,
				"to_currency": "BTN",
				"posting_date": item.currency_exchange_date
			},
			async: false,
			callback: function(vf){
				if(vf.message){
					console.log("here "+String(vf.message))
					// frappe.model.set_value(cdt, cdn, "actual_amount", flt(vf.message)*flt(item.passport_fees) + flt(amount))	
					// frappe.model.set_value(cdt, cdn, "amount", flt(vf.message)*flt(item.passport_fees) + flt(amount))
					if(item.passport_fees_currency != "BTN"){
						frappe.model.set_value(cdt, cdn, "passport_fees_exchange_rate", vf.message);
					}
					// amount = flt(vf.message)*flt(item.passport_fees) + flt(amount)
				}
				
			}
		})
	}
	else {
		// frappe.model.set_value(cdt, cdn, "actual_amount", flt(item.passport_fees) + flt(amount))
		// frappe.model.set_value(cdt, cdn, "total_claim", flt(item.passport_fees) + flt(amount))
		frappe.model.set_value(cdt, cdn, "passport_fees_exchange_rate", 1);
		// amount = flt(item.passport_fees) + flt(amount);
	}
	//If there is incidental expenses
	if(item.incidental_fees_currency != "BTN"){
		frappe.call({
			method: "hrms.hr.doctype.travel_request.travel_request.get_exchange_rate",
			args: {
				"from_currency": item.incidental_fees_currency,
				"to_currency": "BTN",
				"posting_date": item.currency_exchange_date
			},
			async: false,
			callback: function(vf){
				if(vf.message){
					// frappe.model.set_value(cdt, cdn, "actual_amount", flt(vf.message)*flt(item.incidental_fees) + flt(amount))	
					// frappe.model.set_value(cdt, cdn, "amount", flt(vf.message)*flt(item.incidental_fees) + flt(amount))
					if(item.incidental_fees_currency != "BTN"){
						frappe.model.set_value(cdt, cdn, "incidental_expenses_exchange_rate", vf.message);
					}
					// amount = flt(vf.message)*flt(item.incidental_fees) + flt(amount);
				}

			}
		})
	}
	else {
		// frappe.model.set_value(cdt, cdn, "actual_amount", flt(item.incidental_fees) + flt(amount))
		// frappe.model.set_value(cdt, cdn, "amount", flt(item.incidental_fees) + flt(amount))
		frappe.model.set_value(cdt, cdn, "incidental_expenses_exchange_rate", 1);
	}
	var total=0;
	total = flt(item.amount)+flt(item.mileage_amount)+flt(item.fare_amount)+flt(item.entertainment_amount)+flt(item.hotel_charges_amount)+flt(item.visa_fees_exchange_rate*item.visa_fees,2)+flt(item.passport_fees_exchange_rate*item.passport_fees,2)+flt(item.incidental_expenses_exchange_rate*item.incidental_fees,2);
	if(cur_frm.doc.travel_type != "International"){
		total = total + flt(item.porter_pony_charges)
	}
	frappe.model.set_value(cdt, cdn, "total_claim", flt(total));
	frappe.model.set_value(cdt, cdn, "actual_amount", flt(total));
	refresh_field("amount");
	refresh_field("actual_amount");
	refresh_field("total_claim");
}
function update_advance_amount(frm) {
	if(frm.doc.currency!="BTN"){
		frappe.call({
			method: "hrms.hr.doctype.travel_request.travel_request.get_exchange_rate",
			args: {
				"from_currency": frm.doc.currency,
				"to_currency": "BTN",
				"posting_date":frm.doc.posting_date
	
			},
			callback: function(r) {
				if(r.message) {
					frm.set_value("advance_amount_nu", flt(frm.doc.advance_amount) * flt(r.message))
					frm.set_value("exchange_rate", flt(r.message))
				}
			}
		})
	}

}


