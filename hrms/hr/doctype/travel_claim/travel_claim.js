// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("employee", "branch", "branch");
frappe.ui.form.on('Travel Claim', {
	"items_on_form_rendered": function (frm, grid_row, cdt, cdn) {
		/*var row = cur_frm.open_grid_row();
		if(!row.grid_form.fields_dict.dsa_per_day.value) {
			row.grid_form.fields_dict.dsa.set_value(frm.doc.dsa_per_day)
                	row.grid_form.fields_dict.dsa.refresh()
		}*/
	},
	travel_type: function(frm){
		if(frm.doc.travel_type == "Project Visit" || frm.doc.travel_type == "Maintenance"){
			frm.set_value("for_maintenance_project", 1);
		}
		else{
			frm.set_value("for_maintenance_project", 0);
		}
		frm.refresh_field("for_maintenance_project");
	},
	refresh: function (frm) {
		frm.set_query('reference_type', () => {
			return {
				filters: {
					name: ['in', ['Project', 'Maintenance Order']]
				}
			};
		});
		if(frm.doc.workflow_state == "Waiting Project Manager Approval"){
			if(frm.doc.reference_type == "Project" || frm.doc.reference_type == "Task"){
				frm.set_query('reference_name', () => {
					return {
						query: "erpnext.controllers.queries.filter_projects",
						filters: {
							project_manager: frappe.session.user,
							reference_type: frm.doc.reference_type
						}
					};
				});
			}
		}
		if (frm.doc.docstatus == 1) {
			cur_frm.set_df_property("hr_approval", "hidden", 0)
			cur_frm.set_df_property("supervisor_approval", "hidden", 0)

			if (frappe.model.can_read("Journal Entry")) {
				cur_frm.add_custom_button('Bank Entries', function () {
					frappe.route_options = {
						"Journal Entry Account.reference_type": frm.doc.doctype,
						"Journal Entry Account.reference_name": frm.doc.name,
					};
					frappe.set_route("List", "Journal Entry");
				}, __("View"));
			}
		}
		if (frm.doc.reference_type && frm.doc.reference_name) {
			get_project_or_maintenance_cost_center(frm);
		}
	},
	onload: function (frm) {
		if (frm.doc.reference_type && frm.doc.reference_name) {
			get_project_or_maintenance_cost_center(frm);
		}
		cur_frm.set_df_property("supervisor_approval", "hidden", 1)
		cur_frm.set_df_property("hr_approval", "hidden", 1)
		cur_frm.set_df_property("claim_status", "hidden", 1)

		// frm.set_query("supervisor", function () {
		// 	return {
		// 		query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
		// 		filters: {
		// 			employee: frm.doc.employee
		// 		}
		// 	};
		// });
		/*
		if (in_list(frappe.user_roles, "Approver") && frappe.session.user == frm.doc.supervisor) {
			cur_frm.set_df_property("supervisor_approval", "hidden", 0)
			cur_frm.set_df_property("claim_status", "hidden", 0)
		}
		if (in_list(frappe.user_roles, "HR Manager") || in_list(frappe.user_roles, "HR Support"))  {
			cur_frm.set_df_property("hr_approval", "hidden", 0)
			cur_frm.set_df_property("claim_status", "hidden", 0)
		}
		*/

		if (frm.doc.docstatus == 1) {
			//cur_frm.set_df_property("hr_approval", "hidden", 0)
			//cur_frm.set_df_property("supervisor_approval", "hidden", 0)

			//if(frappe.model.can_read("Journal Entry")) {
			cur_frm.add_custom_button('Bank Entries', function () {
				frappe.route_options = {
					"Journal Entry Account.reference_type": frm.doc.doctype,
					"Journal Entry Account.reference_name": frm.doc.name,
				};
				frappe.set_route("List", "Journal Entry");
			});
			//}
		}

		if (frm.doc.docstatus < 2 || frm.doc.__islocal) {
			var ti = frm.doc.items || [];
			var total = 0.0;

			frm.doc.items.forEach(function (d) {
				total += parseFloat(d.actual_amount || 0.0)
			})

			if (parseFloat(total) != parseFloat(frm.doc.total_claim_amount)) {
				frm.set_value("total_claim_amount", parseFloat(total));
			}
		}

	},
	"total_claim_amount": function (frm) {
		frm.set_value("balance_amount", frm.doc.total_claim_amount + frm.doc.extra_claim_amount - frm.doc.advance_amount)
	},
	"extra_claim_amount": function (frm) {
		frm.set_value("balance_amount", frm.doc.total_claim_amount + frm.doc.extra_claim_amount - frm.doc.advance_amount)
	},
	"get_travel_authorization": function (frm) {
		get_travel_detail(frm);
	},
	"reference_name": function (frm) {
		if (frm.doc.reference_type) {
			get_project_or_maintenance_cost_center(frm)
		}
	}

});

function get_project_or_maintenance_cost_center(frm) {
	frappe.db.get_value(frm.doc.reference_type, frm.doc.reference_name, 'cost_center', (r) => {
		frm.doc.cost_center = r.cost_center
		cur_frm.refresh_field("cost_center")
	})
}

frappe.ui.form.on("Travel Claim Item", {
	"form_render": function (frm, cdt, cdn) {
		
		frappe.model.set_value(cdt, cdn, "travel_authorization", frm.doc.ta);
		frappe.model.set_value(cdt, cdn, "currency_exchange_date", frm.doc.ta_date);
		frm.refresh_field("items");
		var item = frappe.get_doc(cdt, cdn)
		
		if (item.idx!=0){
			// console.log(frm.fields_dict['items'].grid.grid_rows_by_docname[cdn]);
			frm.fields_dict['items'].grid.grid_rows_by_docname[cdn].docfields[3].read_only=0
			frappe.model.set_value(cdt, cdn, "halt", 0)
			

		}
		if (item.halt==0){
			frm.fields_dict['items'].grid.grid_rows_by_docname[cdn].toggle_editable('to_place', true)
			frm.fields_dict['items'].grid.grid_rows_by_docname[cdn].toggle_editable('from_place', true)
		}
		frm.refresh_field("items");
		if (frm.doc.__islocal) {
			var item = frappe.get_doc(cdt, cdn)
			// if (item.halt == 0) {
			// 	var df = frappe.meta.get_docfield("Travel Claim Item", "distance", cur_frm.doc.name);
			// 	frappe.model.set_value(cdt, cdn, "distance", "")
			// 	//df.display = 0;
			// }

			// if (item.currency != "BTN") {
			// 	frappe.model.set_value(cdt, cdn, "amount", format_currency(flt(item.amount), item.currency))
			// }
		}
	},
	"currency": function (frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"visa_fees_currency": function (frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"passport_fees_currency": function (frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"incidental_fees_currency": function (frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"dsa": function (frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"porter_pony_charges": function (frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"visa_fees": function (frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"passport_fees": function (frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"incidental_fees": function (frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"mileage_rate": function (frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"distance": function (frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"dsa_percent": function (frm, cdt, cdn) {
		do_update(frm, cdt, cdn)
	},
	"actual_amount": function (frm, cdt, cdn) {
		var total = 0;
		frm.doc.items.forEach(function (d) {
			total += d.actual_amount
		})
		frm.set_value("total_claim_amount", total)
	},
	"date": function (frm, cdt, cdn) {
		update_days(frm, cdt, cdn);
		var items = frappe.get_doc(cdt, cdn)
		if(items.halt==0){
			frappe.model.set_value(cdt, cdn, "till_date", items.date)
		}
	},
	"till_date": function (frm, cdt, cdn) {
		update_days(frm, cdt, cdn);
	},
})

function update_days(frm, cdt, cdn){
	frm.doc.items.forEach(function (d) {
		if(d.halt==1){
			const date1=new Date(d.date);
			const date2=new Date(d.till_date);
			let no_days=(date2-date1)/ (1000*60*60*24);
			no_days+=1
			console.log(no_days);
			frappe.model.set_value(cdt, cdn, "no_days", String(no_days))


		}
	})
	do_update(frm, cdt, cdn)
}
function get_travel_detail(form) {
	if (form.doc.start_date && form.doc.end_date && form.doc.place_type && form.doc.travel_type) {
		frappe.call({
			method: "hrms.hr.doctype.travel_claim.travel_claim.get_travel_detail",
			async: false,
			args: {
				"employee": form.doc.employee,
				"start_date": form.doc.start_date,
				"end_date": form.doc.end_date,
				"place_type": form.doc.place_type,
				"travel_type": form.doc.travel_type
			},
			callback: function (r) {
				if (r.message) {
					var total_advance_amount = 0;
					var total_claim_amount = 0;
					var dsa_per_day = 0;
					cur_frm.clear_table("items");
					r.message.forEach(function (dtl) {
						var row = frappe.model.add_child(cur_frm.doc, "Travel Claim Item", "items");
						row.halt = dtl['halt'];
						row.from_place = dtl['from_place'];
						row.to_place = dtl['to_place'];
						row.date = dtl['date'];
						row.no_days = dtl['no_days'];
						row.days_allocated = dtl['no_days']
						row.till_date = dtl['till_date'];
						row.halt_at = dtl['halt_at'];
						row.travel_authorization = dtl['name'];
						row.last_day = dtl['last_day'];
						row.dsa = dtl['dsa_per_day'];
						dsa_per_day = dtl['dsa_per_day'];
						row.dsa_percent = dtl['dsa_percent'];
						row.currency = dtl['currency'];
						row.exchange_rate = dtl['exchange_rate'];
						var amount = dtl['no_days'] * (dtl['dsa_per_day'] * (dtl['dsa_percent'] / 100));
						var actual_amount = dtl['no_days'] * (dtl['dsa_per_day'] * (dtl['dsa_percent'] / 100)) * dtl['exchange_rate'];
						row.amount = amount;
						row.actual_amount = actual_amount;
						total_claim_amount += actual_amount;
						total_advance_amount += dtl['advance_amount'];
					});
					form.set_value("total_claim_amount", total_claim_amount);
					form.set_value("advance_amount", total_advance_amount);
					form.set_value("balance_amount", total_claim_amount - total_advance_amount);
					form.set_value("dsa_per_day", dsa_per_day);
					cur_frm.refresh();
				}
				else {
					frappe.msgprint("No unclaimed Travel Authorization found!")
				}
			}
		});

	} else {
		frappe.msgprint("Start Date, End Date, Place Type and Travel Purpose not be selected before");
	}

}

function do_update(frm, cdt, cdn) {
	//var item = frappe.get_doc(cdt, cdn)
	var item = locals[cdt][cdn]
	/*if (item.last_day) {
		item.dsa_percent = 0
	} */
	var amount = 0;
	if(frm.doc.place_type == "In-Country"){
		amount = flt((flt(item.dsa_percent) / 100 * flt(item.dsa)) + (flt(item.mileage_rate) * flt(item.distance)) + flt(item.porter_pony_charges) + flt(item.fare_amount)) 
		if (item.halt == 1) {
			amount = flt((flt(item.dsa_percent) / 100 * flt(item.dsa)) * flt(item.no_days))+flt(item.porter_pony_charges);
		}
	}
	else if(frm.doc.place_type == "Out-Country"){
		amount = flt((flt(item.dsa_percent) / 100 * flt(item.dsa)) + (flt(item.mileage_rate) * flt(item.distance)) + flt(item.fare_amount)); 
		if (item.halt == 1) {
			amount = flt((flt(item.dsa_percent) / 100 * flt(item.dsa)) * flt(item.no_days));
		}
	}
	if (item.currency != "BTN") {
		frappe.call({
			method: "hrms.hr.doctype.travel_authorization.travel_authorization.get_exchange_rate",
			args: {
				"from_currency": item.currency,
				"to_currency": "BTN",
				"date": item.currency_exchange_date
			},
			async:false,
			callback: function (r) {
				if (r.message) {
					frappe.model.set_value(cdt, cdn, "exchange_rate", flt(r.message))
					frappe.model.set_value(cdt, cdn, "actual_amount", flt(r.message) * flt(amount))
					frappe.model.set_value(cdt, cdn, "amount", flt(r.message) * flt(amount))
					amount = flt(r.message) * flt(amount);
				}
			}
		})
	}
	else {
		frappe.model.set_value(cdt, cdn, "actual_amount", flt(amount));
		frappe.model.set_value(cdt, cdn, "amount", flt(amount));
	}
	//If there is visa fee
	if(item.visa_fees_currency != "BTN"){
		frappe.call({
			method: "hrms.hr.doctype.travel_authorization.travel_authorization.get_exchange_rate",
			args: {
				"from_currency": item.visa_fees_currency,
				"to_currency": "BTN",
				"date": item.currency_exchange_date
			},
			async: false,
			callback: function(vf){
				if(vf.message){
					frappe.model.set_value(cdt, cdn, "actual_amount", flt(vf.message)*flt(item.visa_fees) + flt(amount))	
					frappe.model.set_value(cdt, cdn, "amount", flt(vf.message)*flt(item.visa_fees) + flt(amount))
					amount = flt(vf.message)*flt(item.visa_fees) + flt(amount);
				}

			}
		})
	}
	else {
		frappe.model.set_value(cdt, cdn, "actual_amount", flt(item.visa_fees) + flt(amount))
		frappe.model.set_value(cdt, cdn, "amount", flt(item.visa_fees) + flt(amount))
		amount = flt(item.visa_fees) + flt(amount)
	}
	//If there is passport fee
	if(item.passport_fees_currency != "BTN"){
		frappe.call({
			method: "hrms.hr.doctype.travel_authorization.travel_authorization.get_exchange_rate",
			args: {
				"from_currency": item.passport_fees_currency,
				"to_currency": "BTN",
				"date": item.currency_exchange_date
			},
			async: false,
			callback: function(vf){
				if(vf.message){
					frappe.model.set_value(cdt, cdn, "actual_amount", flt(vf.message)*flt(item.passport_fees) + flt(amount))	
					frappe.model.set_value(cdt, cdn, "amount", flt(vf.message)*flt(item.passport_fees) + flt(amount))
					amount = flt(vf.message)*flt(item.passport_fees) + flt(amount)
				}

			}
		})
	}
	else {
		frappe.model.set_value(cdt, cdn, "actual_amount", flt(item.passport_fees) + flt(amount))
		frappe.model.set_value(cdt, cdn, "amount", flt(item.passport_fees) + flt(amount))
		amount = flt(item.passport_fees) + flt(amount);
	}
	//If there is incidental expenses
	if(item.incidental_fees_currency != "BTN"){
		frappe.call({
			method: "hrms.hr.doctype.travel_authorization.travel_authorization.get_exchange_rate",
			args: {
				"from_currency": item.incidental_fees_currency,
				"to_currency": "BTN",
				"date": item.currency_exchange_date
			},
			async: false,
			callback: function(vf){
				if(vf.message){
					frappe.model.set_value(cdt, cdn, "actual_amount", flt(vf.message)*flt(item.incidental_fees) + flt(amount))	
					frappe.model.set_value(cdt, cdn, "amount", flt(vf.message)*flt(item.incidental_fees) + flt(amount))
					amount = flt(vf.message)*flt(item.incidental_fees) + flt(amount);
				}

			}
		})
	}
	else {
		frappe.model.set_value(cdt, cdn, "actual_amount", flt(item.incidental_fees) + flt(amount))
		frappe.model.set_value(cdt, cdn, "amount", flt(item.incidental_fees) + flt(amount))
	}
	// frappe.model.set_value(cdt, cdn, "amount", format_currency(amount, item.currency))
	refresh_field("amount");
	refresh_field("actual_amount");

}

frappe.ui.form.on("Travel Claim", "after_save", function (frm, cdt, cdn) {
	if (in_list(frappe.user_roles, "Approver")) {
		if (frm.doc.workflow_state && frm.doc.workflow_state.indexOf("Rejected") >= 0) {
			frappe.prompt([
				{
					fieldtype: 'Small Text',
					reqd: true,
					fieldname: 'reason'
				}],
				function (args) {
					validated = true;
					frappe.call({
						method: 'frappe.core.doctype.communication.email.make',
						args: {
							doctype: frm.doctype,
							name: frm.docname,
							subject: format(__('Reason for {0}'), [frm.doc.workflow_state]),
							content: args.reason,
							send_mail: false,
							send_me_a_copy: false,
							communication_medium: 'Other',
							sent_or_received: 'Sent'
						},
						callback: function (res) {
							if (res && !res.exc) {
								frappe.call({
									method: 'frappe.client.set_value',
									args: {
										doctype: frm.doctype,
										name: frm.docname,
										fieldname: 'reason',
										value: frm.doc.reason ?
											[frm.doc.reason, '[' + String(frappe.session.user) + ' ' + String(frappe.datetime.nowdate()) + ']' + ' : ' + String(args.reason)].join('\n') : frm.doc.workflow_state
									},
									callback: function (res) {
										if (res && !res.exc) {
											frm.reload_doc();
										}
									}
								});
							}
						}
					});
				},
				__('Reason for ') + __(frm.doc.workflow_state),
				__('Save')
			)
		}
	}
});

// frappe.ui.form.on('Travel Claim Item',{
// 	date: function(frm, cdt, cdn){
// 		update_auth(frm, cdt, cdn)	
// 	}
// })
// function update_auth(frm, cdt, cdn){
// 	var item = locals[cdt][cdn]
// 	frappe.call({
// 		method: "erpnext.hr.doctype.travel_authorization.travel_authorization.update_date_authorization",
// 		args: {
// 			"idIdx":item.idx,
// 			"auth_date": item.date,
// 			"ta_id": item.travel_authorization
// 		}
// 	})
//  }