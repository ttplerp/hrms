// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Overtime Application', {
	onload: function(frm) {
		if(!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today())
		}
	},
	refresh: function(frm){
		//enable_disable(frm);
		// frm.set_query("approver", function() {
        //                 return {
        //                         query: "erpnext.custom_workflow.approver_list",
        //                         filters: {
        //                                 employee: frm.doc.employee
        //                         }
        //                 };
        //         });	
		//set_approver(frm);
	},
	
	// approver: function(frm) {
	// 	if(frm.doc.approver){
	// 		frm.set_value("approver_name", frappe.user.full_name(frm.doc.approver));
	// 	}
	// },
	
	rate: function(frm) {
		frm.set_value("total_amount", flt(frm.doc.rate) * flt(frm.doc.total_hours))
	},
	
	employee: function(frm){
		frappe.call({
			method:'check_for_overtime_eligibility',
			doc: frm.doc,
			callback:function(r){
			}
		})
	},

});

frappe.ui.form.on("Overtime Application Item", {
	"number_of_hours": function(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn)
		calculate_time(frm, cdt, cdn);
	},
	"rate":function(frm, cdt, cdn){
		calculate_amount(frm, cdt, cdn)
	},
	"from_date": function(frm, cdt, cdn) {
		var child = locals[cdt][cdn]
		var hours = moment(child.to_date).diff(moment(child.from_date), "seconds") / 3600;
		if(child.to_date && child.from_date) {
			frappe.model.set_value(cdt, cdn, "number_of_hours", hours);
		}
		if (frm.doc.employee) {
			frappe.call({
				method: "erpnext.setup.doctype.employee.employee.get_overtime_rate",
				args: {
					employee: frm.doc.employee,
					posting_date:child.from_date
				},
				callback: function(r) {
					if(r.message) {
						// frm.set_value("rate", r.message)
						frappe.model.set_value(cdt, cdn, "rate", r.message);
					}
				}
			})
		}
	},
	
	"to_date": function(frm, cdt, cdn) {
        	var child = locals[cdt][cdn]
        	var hours = moment(child.to_date).diff(moment(child.from_date), "seconds") / 3600;
        	if(child.to_date && child.from_date) {
				frappe.model.set_value(cdt, cdn, "number_of_hours", hours);
				}
        },


	items_remove: function(frm, cdt, cdn) {
		calculate_time(frm, cdt, cdn);
	},
	
})
function calculate_amount(frm, cdt, cdn){
	let row = locals[cdt][cdn]
	if (row.number_of_hours && row.rate){
		frappe.model.set_value(cdt, cdn, "amount", row.rate * row.number_of_hours);
	}
}
function calculate_time(frm, cdt, cdn) {
	let total_time = 0;
	let total_amount = 0
	frm.doc.items.forEach(function(d) {
		if(d.number_of_hours && d.rate) {
			total_time += d.number_of_hours
			total_amount += d.amount
		}	
	})
	frm.set_value("total_hours", total_time)
	frm.set_value("total_amount", total_amount)
	cur_frm.refresh_field("total_hours")
	cur_frm.refresh_field("total_amount")
}

function toggle_form_fields(frm, fields, flag){
	fields.forEach(function(field_name){
		frm.set_df_property(field_name, "read_only", flag);
	});
	
	if(flag){
		frm.disable_save();
	} else {
		frm.enable_save();
	}
}

function enable_disable(frm){
	var toggle_fields = [];
	var meta = frappe.get_meta(frm.doctype);

	for(var i=0; i<meta.fields.length; i++){
		if(meta.fields[i].hidden === 0 && meta.fields[i].read_only === 0 && meta.fields[i].allow_on_submit === 0){
			toggle_fields.push(meta.fields[i].fieldname);
		}
	}
	
	toggle_form_fields(frm, toggle_fields, 1);
	
	if(frm.doc.__islocal){
		toggle_form_fields(frm, toggle_fields, 0);
	}
	else {
		// Request Creator
		// if(in_list(user_roles, "Employee") && (frm.doc.workflow_state.indexOf("Draft") >= 0 || frm.doc.workflow_state.indexOf("Rejected") >= 0)){
		// 	if(frappe.session.user === frm.doc.owner){
		// 		toggle_form_fields(frm, toggle_fields, 0);
		// 	}
		// }
		
		// // OT Supervisor
		// if(in_list(user_roles, "OT Supervisor") && frm.doc.workflow_state.indexOf("Waiting Approval") >= 0){
		// 	if(frappe.session.user != frm.doc.owner){
		// 		toggle_form_fields(frm, toggle_fields, 0);
		// 	}
		// }
		
		// // OT Approver
		// if(in_list(user_roles, "OT Approver") && frm.doc.workflow_state.indexOf("Verified by Supervisor") >= 0){
		// 	toggle_form_fields(frm, toggle_fields, 0);
		// }
	}
}

frappe.ui.form.on("Overtime Application", "after_save", function(frm, cdt, cdn){
	if(in_list(user_roles, "OT Supervisor") || in_list(user_roles, "OT Approver")){
		if (frm.doc.workflow_state && frm.doc.workflow_state.indexOf("Rejected") >= 0){
			frappe.prompt([
				{
					fieldtype: 'Small Text',
					reqd: true,
					fieldname: 'reason'
				}],
				function(args){
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
						callback: function(res){
							if (res && !res.exc){
								frappe.call({
									method: 'frappe.client.set_value',
									args: {
										doctype: frm.doctype,
										name: frm.docname,
										fieldname: 'rejection_reason',
										value: frm.doc.rejection_reason ?
											[frm.doc.rejection_reason, '['+String(frappe.session.user)+' '+String(frappe.datetime.nowdate())+']'+' : '+String(args.reason)].join('\n') : frm.doc.workflow_state
									},
									callback: function(res){
										if (res && !res.exc){
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
