// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
{% include "erpnext/public/js/controllers/accounts.js" %}

cur_frm.add_fetch('company', 'default_letter_head', 'letter_head');
cur_frm.add_fetch('employee', 'company', 'company');

frappe.ui.form.on('Salary Structure', {
	onload: function(frm, cdt, cdn){
		// Following function is created as a replacement for the following commented block by SHIV on 2020/09/23
		make_ed_table(frm);
		/*
		e_tbl = frm.doc.earnings || [];
		d_tbl = frm.doc.deductions || [];
		
		if (e_tbl.length == 0 && d_tbl.length == 0){
			cur_frm.call({
				method: "make_earn_ded_table",
				doc: frm.doc
			});
		}
		*/
	},
	onload_post_render: function(frm) {
		highlight_expired_components(frm);
	},
	refresh: function(frm, cdt, cdn) {
		// Following code is commented by SHIV on 2020/09/23
		/*
		frm.trigger("toggle_fields")
		frm.fields_dict['earnings'].grid.set_column_disp("default_amount", false);
		frm.fields_dict['deductions'].grid.set_column_disp("default_amount", false);
		frm.fields_dict['earnings'].grid.set_column_disp("sb_additional_info", false);
		*/		
		// Commented till here by SHIV on 2020/09/23

		/*
		if((!frm.doc.__islocal) && (frm.doc.is_active == 'Yes') && cint(frm.doc.salary_slip_based_on_timesheet == 0)){
			cur_frm.add_custom_button(__('Salary Slip'),
				cur_frm.cscript['Make Salary Slip'], __("Make"));
			cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
		}
		*/
		hide_eligible_boxes(frm);
	},
	employee: function(frm, cdt, cdn){
		if (frm.doc.employee) {
			cur_frm.call({
				method: "get_employee_details",
				doc: frm.doc
			});
		}
		calculate_others(frm);
	},
	is_active: function(frm){
		frm.toggle_reqd("to_date", frm.doc.is_active == "No");
	},
	salary_slip_based_on_timesheet: function(frm) {
		frm.trigger("toggle_fields")
	},
	toggle_fields: function(frm) {
		frm.toggle_display(['salary_component', 'hour_rate'], frm.doc.salary_slip_based_on_timesheet);
		frm.toggle_reqd(['salary_component', 'hour_rate'], frm.doc.salary_slip_based_on_timesheet);
	},
	eligible_for_corporate_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_contract_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_communication_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_fuel_allowances: function(frm){
		calculate_others(frm);
	},
	eligible_for_underground: function(frm){
		calculate_others(frm);
	},
	eligible_for_shift: function(frm){
		calculate_others(frm);
	},
	eligible_for_difficulty: function(frm){
		calculate_others(frm);
	},
	eligible_for_high_altitude: function(frm){
		calculate_others(frm);
	},
	eligible_for_psa: function(frm){
		calculate_others(frm);
	},
	eligible_for_pda: function(frm){
		calculate_others(frm);
	},
	eligible_for_deputation: function(frm){
		calculate_others(frm);
	},
	eligible_for_officiating_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_temporary_transfer_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_scarcity: function(frm){
		calculate_others(frm);
	},
	eligible_for_cash_handling: function(frm){
		calculate_others(frm);
	},
	eligible_for_honorarium: function(frm){
		calculate_others(frm);
	},
	eligible_for_fixed_allowance: function(frm){
		calculate_others(frm);
	},
	fixed_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_talent_retention_allowance: function(frm){
		calculate_others(frm);
	},
	talent_retention_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_mpi: function(frm){
		calculate_others(frm);
	},
	eligible_for_security_deposit: function(frm){
		calculate_others(frm);
	},
	eligible_for_sws: function(frm){
		calculate_others(frm);
	},
	eligible_for_gis: function(frm){
		calculate_others(frm);
	},
	eligible_for_pf: function(frm){
		calculate_others(frm);
	},
	eligible_for_health_contribution: function(frm){
		calculate_others(frm);
	},
	eligible_for_banking_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_atm_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_driver_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_house_rent_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_joint_custodian: function(frm){
		calculate_others(frm);
	},
	eligible_for_entertainment_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_project_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_special_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_holiday_banking: function(frm){
		calculate_others(frm);
	},
	eligible_for_uniform_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_house_rent_deduction: function(frm){
		calculate_others(frm);
	},
	ca: function(frm){
		calculate_others(frm);
	},
	contract_allowance: function(frm){
		calculate_others(frm);
	},
	communication_allowance: function(frm){
		calculate_others(frm);
	},
	psa: function(frm){
		calculate_others(frm);
	},
	mpi: function(frm){
		calculate_others(frm);
	},
	officiating_allowance: function(frm){
		calculate_others(frm);
	},
	temporary_transfer_allowance: function(frm){
		calculate_others(frm);
	},
	/*
	lumpsum_temp_transfer_amount: function(frm) {
		calculate_others(frm);
		calculate_totals(frm.doc);
	},
	*/
	fuel_allowances: function(frm){
		calculate_others(frm);
	},
	pda: function(frm){
		calculate_others(frm);
	},
	shift: function(frm){
		calculate_others(frm);
	},
	deputation: function(frm){
		calculate_others(frm);
	},
	underground: function(frm){
		calculate_others(frm);
	},
	difficulty: function(frm){
		calculate_others(frm);
	},
	high_altitude: function(frm){
		calculate_others(frm);
	},
	scarcity: function(frm){
		calculate_others(frm);
	},
	cash_handling: function(frm){
		calculate_others(frm);
	},
	honorarium: function(frm){
		calculate_others(frm);
	},
	banking_allowance: function(frm){
		calculate_others(frm);
	},
	atm_allowance: function(frm){
		calculate_others(frm);
	},
	driver_allowance: function(frm){
		calculate_others(frm);
	},
	house_rent_allowance: function(frm){
		calculate_others(frm);
	},
	joint_custodian: function(frm){
		calculate_others(frm);
	},
	entertainment_allowance: function(frm){
		calculate_others(frm);
	},
	project_allowance: function(frm){
		calculate_others(frm);
	},
	special_allowance: function(frm){
		calculate_others(frm);
	},
	holiday_banking: function(frm){
		calculate_others(frm);
	},
	uniform_allowance: function(frm){
		calculate_others(frm);
	},
	// Payment Methods
	ca_method: function(frm){
		calculate_others(frm);
	},
	contract_allowance_method: function(frm){
		calculate_others(frm);
	},
	communication_allowance_method: function(frm){
		calculate_others(frm);
	},
	psa_method: function(frm){
		calculate_others(frm);
	},
	mpi_method: function(frm){
		calculate_others(frm);
	},
	officiating_allowance_method: function(frm){
		calculate_others(frm);
	},
	temporary_transfer_allowance_method: function(frm){
		calculate_others(frm);
	},
	fuel_allowances_method: function(frm){
		calculate_others(frm);
	},
	pda_method: function(frm){
		calculate_others(frm);
	},
	shift_method: function(frm){
		calculate_others(frm);
	},
	deputation_method: function(frm){
		calculate_others(frm);
	},
	underground_method: function(frm){
		calculate_others(frm);
	},
	difficulty_method: function(frm){
		calculate_others(frm);
	},
	high_altitude_method: function(frm){
		calculate_others(frm);
	},
	scarcity_method: function(frm){
		calculate_others(frm);
	},
	cash_handling_method: function(frm){
		calculate_others(frm);
	},
	honorarium_method: function(frm){
		calculate_others(frm);
	},
	banking_allowance_method: function(frm){
		calculate_others(frm);
	},
	atm_allowance_method: function(frm){
		calculate_others(frm);
	},
	driver_allowance_method: function(frm){
		calculate_others(frm);
	},
	house_rent_allowance_method: function(frm){
		calculate_others(frm);
	},
	joint_custodian_method: function(frm){
		calculate_others(frm);
	},
	entertainment_allowance_method: function(frm){
		calculate_others(frm);
	},
	project_allowance_method: function(frm){
		calculate_others(frm);
	},
	special_allowance_method: function(frm){
		calculate_others(frm);
	},
	holiday_banking_method: function(frm){
		calculate_others(frm);
	},
	uniform_allowance_method: function(frm){
		calculate_others(frm);
	},
	eligible_for_tswf:function(frm){
		calculate_others(frm);
	}
})

// dynamically display checkboxes based on Salary Component's status
var hide_eligible_boxes = function(frm){
	frappe.call({
		method: 'frappe.client.get_list',
		args: {
				doctype: 'Salary Component',
				fields: ['field_name', 'field_method', 'field_value', 'enabled'],
		},
		callback: function(r){
			if(r.message){
				r.message.forEach(function(row, i){
					if(row.field_name){
						if(frm.doc[row.field_name] == 1){
							// do nothing if the component is already checked
						} else {
							cur_frm.toggle_display(row.field_name, row.enabled);
							// cur_frm.toggle_display(row.field_method, row.enabled);
							// cur_frm.toggle_display(row.field_value, row.enabled);
						}
					}
				});
			}
		}
	});
}

var make_ed_table = function(frm){
	var e_tbl = frm.doc.earnings || [];
	var d_tbl = frm.doc.deductions || [];
	
	if (e_tbl.length == 0 && d_tbl.length == 0){
		cur_frm.call({
			method: "make_earn_ded_table",
			doc: frm.doc
		});
	}
}


var highlight_rows = function(frm, earn_ded_tbl){
	let highlight = 0;
	(frm.doc[earn_ded_tbl] || []).forEach(function(rec, i){
		highlight = 0;
		if(rec.from_date || rec.to_date){
			if (!((rec.to_date && rec.to_date >= frappe.datetime.month_start()) ||
				(rec.from_date && rec.from_date <= frappe.datetime.month_end()))) {
				highlight = 1;
			}
		}

		if(rec.parentfield == "deductions" && flt(rec.total_deductible_amount) 
				&& flt(rec.total_deductible_amount) == flt(rec.total_deducted_amount)){
			highlight = 1;
		}

		if(highlight){
			$(`div.grid-row[data-name='${rec.name}']`).find("div[data-fieldname='amount']").css({"color": "red"});
		} else {
			$(`div.grid-row[data-name='${rec.name}']`).find("div[data-fieldname='amount']").css({"color": "#555"});
		}
	});
}

var highlight_expired_components = function(frm){
	["earnings", "deductions"].forEach(function(tbl, i){highlight_rows(frm, tbl);})
}

frappe.ui.form.on('Salary Detail', {
	amount: function(frm, cdt, cdn) {
		calculate_others(frm);
	},
	
	earnings_remove: function(frm) {
		calculate_others(frm);
	}, 
	
	// commented as the version 12 is giving issue 2021/04/06
	// deductions_remove: function(frm) {
	// 	calculate_others(frm);
	// },
	
	total_deductible_amount: function(frm, cdt, cdn){
		var d = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "total_outstanding_amount", parseFloat(d.total_deductible_amount || 0.0)-parseFloat(d.total_deducted_amount || 0.0));
	},

	from_date: function(frm){
		highlight_expired_components(frm);
	},

	to_date: function(frm){
		highlight_expired_components(frm);
	},
})

// commented as the version 12 is giving issue 2021/04/06
// function calculate_others(frm) {
// 	frappe.call({
// 		method: "update_salary_structure",
// 		doc: frm.doc,
// 		callback: function (r) {
// 			// frm.refresh_field("earnings");
// 			// frm.refresh_field("deductions");
// 			frm.refresh_fields();
// 		},
// 		freeze: true,
// 		freeze_message: "Recalculating..."
// 	});
// }


function calculate_others(frm) {
	frappe.call({
		method: "update_salary_structure",
		doc: frm.doc,
		args: {"remove_flag": 0},
		callback: function (r) {
			if(r.message){
				// earnings
				if(frm.doc.earnings){
					frm.doc.earnings.forEach(function(i,j){
						r.message.forEach(function(k,l){
							if(k.name==i.name){
								cur_frm.get_field("earnings").grid.grid_rows[j].remove();
							}
						})
					});
				}

				// deductions
				if(frm.doc.deductions){
					frm.doc.deductions.forEach(function(i,j){
						r.message.forEach(function(k,l){
							if(k.name==i.name){
								cur_frm.get_field("deductions").grid.grid_rows[j].remove();
							}
						})
					});
				}
			}
			// frm.refresh_field("earnings");
			// frm.refresh_field("deductions");
			frm.refresh_fields();
		},
		freeze: true,
		freeze_message: "Recalculating..."
	});
}

cur_frm.fields_dict.employee.get_query = function(doc,cdt,cdn) {
			return{ query: "erpnext.controllers.queries.employee_query" }
}

cur_frm.cscript['Make Salary Slip'] = function() {
	frappe.model.open_mapped_doc({
		method: "hrms.hr.hr_custom_functions.make_salary_slip",
		frm: cur_frm
	});
}

// ++++++++++++++++++++ Ver 2.0 BEGINS ++++++++++++++++++++
// Following code added by SHIV on 2018/02/27
frappe.ui.form.on("Salary Structure", "refresh", function(frm) {
    frm.fields_dict['earnings'].grid.get_field('salary_component').get_query = function(doc, cdt, cdn) {
        var doc = locals[cdt][cdn];
        return {
            "query": "hrms.payroll.doctype.salary_structure.salary_structure.salary_component_query",
            filters: {'parentfield': 'earnings'}
        }
    };
});

frappe.ui.form.on("Salary Structure", "refresh", function(frm) {
    frm.fields_dict['deductions'].grid.get_field('salary_component').get_query = function(doc, cdt, cdn) {
        doc = locals[cdt][cdn]
        return {
            "query": "hrms.payroll.doctype.salary_structure.salary_structure.salary_component_query",
            filters: {'parentfield': 'deductions'}
        }
    };
});
// +++++++++++++++++++++ Ver 2.0 ENDS +++++++++++++++++++++





























// cur_frm.cscript.onload = function(doc, dt, dn){
// 	var e_tbl = doc.earnings || [];
// 	var d_tbl = doc.deductions || [];
// 	if (e_tbl.length == 0 && d_tbl.length == 0)
// 		return function(r, rt) { refresh_many(['earnings', 'deductions']);};
// }

// frappe.ui.form.on('Salary Structure', {
// 	onload: function(frm) {

// 		let help_button = $(`<a class = 'control-label'>
// 			${__("Condition and Formula Help")}
// 		</a>`).click(()=>{

// 			let d = new frappe.ui.Dialog({
// 				title: __('Condition and Formula Help'),
// 				fields: [
// 					{
// 						fieldname: 'msg_wrapper',
// 						fieldtype: 'HTML'
// 					}
// 				]
// 			});

// 			let message_html = frappe.render_template("condition_and_formula_help")

// 			d.fields_dict.msg_wrapper.$wrapper.append(message_html)

// 			d.show()
// 		});
// 		let help_button_wrapper = frm.get_field("conditions_and_formula_variable_and_example").$wrapper;
// 		help_button_wrapper.empty();
// 		help_button_wrapper.append(frm.doc.filters_html).append(help_button)

// 		frm.toggle_reqd(['payroll_frequency'], !frm.doc.salary_slip_based_on_timesheet)

// 		frm.set_query("payment_account", function () {
// 			var account_types = ["Bank", "Cash"];
// 			return {
// 				filters: {
// 					"account_type": ["in", account_types],
// 					"is_group": 0,
// 					"company": frm.doc.company
// 				}
// 			};
// 		});
// 		frm.trigger('set_earning_deduction_component');
// 	},

// 	set_earning_deduction_component: function(frm) {
// 		if(!frm.doc.company) return;
// 		frm.set_query("salary_component", "earnings", function() {
// 			return {
// 				filters: {type: "earning", company: frm.doc.company}
// 			};
// 		});
// 		frm.set_query("salary_component", "deductions", function() {
// 			return {
// 				filters: {type: "deduction", company: frm.doc.company}
// 			};
// 		});
// 	},

// 	company: function(frm) {
// 		frm.trigger('set_earning_deduction_component');
// 	},

// 	currency: function(frm) {
// 		calculate_totals(frm.doc);
// 		frm.trigger("set_dynamic_labels")
// 		frm.refresh()
// 	},

// 	set_dynamic_labels: function(frm) {
// 		frm.set_currency_labels(["net_pay","hour_rate", "leave_encashment_amount_per_day", "max_benefits", "total_earning",
// 			"total_deduction"], frm.doc.currency);

// 		frm.set_currency_labels(["amount", "additional_amount", "tax_on_flexible_benefit", "tax_on_additional_salary"],
// 			frm.doc.currency, "earnings");

// 		frm.set_currency_labels(["amount", "additional_amount", "tax_on_flexible_benefit", "tax_on_additional_salary"],
// 			frm.doc.currency, "deductions");

// 		frm.refresh_fields();
// 	},

// 	refresh: function(frm) {
// 		frm.trigger("set_dynamic_labels")
// 		frm.trigger("toggle_fields");
// 		frm.fields_dict['earnings'].grid.set_column_disp("default_amount", false);
// 		frm.fields_dict['deductions'].grid.set_column_disp("default_amount", false);

// 		if(frm.doc.docstatus === 1) {
// 			frm.add_custom_button(__("Preview Salary Slip"), function() {
// 				frm.trigger('preview_salary_slip');
// 			});
// 		}

// 		if(frm.doc.docstatus==1) {
// 			frm.add_custom_button(__("Assign Salary Structure"), function() {
// 				var doc = frappe.model.get_new_doc('Salary Structure Assignment');
// 				doc.salary_structure = frm.doc.name;
// 				doc.company = frm.doc.company;
// 				frappe.set_route('Form', 'Salary Structure Assignment', doc.name);
// 			});
// 			frm.add_custom_button(__("Assign to Employees"),function () {
// 				frm.trigger('assign_to_employees')
// 			})
// 		}

// 		// set columns read-only
// 		let fields_read_only = ["is_tax_applicable", "is_flexible_benefit", "variable_based_on_taxable_salary"];
// 		fields_read_only.forEach(function(field) {
// 			frm.fields_dict.earnings.grid.update_docfield_property(
// 				field, 'read_only', 1
// 			);
// 			frm.fields_dict.deductions.grid.update_docfield_property(
// 				field, 'read_only', 1
// 			);
// 		});
// 		frm.trigger('set_earning_deduction_component');
// 	},
// 	eligible_for_corporate_allowance: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_contract_allowance: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_communication_allowance: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_fuel_allowances: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_underground: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_shift: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_difficulty: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_high_altitude: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_psa: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_pda: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_deputation: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_officiating_allowance: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_temporary_transfer_allowance: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_scarcity: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_cash_handling: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_honorarium: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_mpi: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_sws: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_gis: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_pf: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	eligible_for_health_contribution: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	ca: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	contract_allowance: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	communication_allowance: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	psa: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	mpi: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	officiating_allowance: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	temporary_transfer_allowance: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	/*
// 	lumpsum_temp_transfer_amount: function(frm) {
// 		calculate_others(frm.doc);
// 		calculate_totals(frm.doc);
// 	},
// 	*/
// 	fuel_allowances: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	pda: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	shift: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	deputation: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	underground: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	difficulty: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	high_altitude: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	scarcity: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	cash_handling: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	honorarium: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	// Payment Methods
// 	ca_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	contract_allowance_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	communication_allowance_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	psa_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	mpi_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	officiating_allowance_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	temporary_transfer_allowance_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	fuel_allowances_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	pda_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	shift_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	deputation_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	underground_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	difficulty_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	high_altitude_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	scarcity_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	cash_handling_method: function(frm){
// 		calculate_others(frm.doc);
// 	},
// 	honorarium_method: function(frm){
// 		calculate_others(frm.doc);
// 	},

// 	assign_to_employees:function (frm) {
// 		var d = new frappe.ui.Dialog({
// 			title: __("Assign to Employees"),
// 			fields: [
// 				{fieldname: "sec_break", fieldtype: "Section Break", label: __("Filter Employees By (Optional)")},
// 				{fieldname: "grade", fieldtype: "Link", options: "Employee Grade", label: __("Employee Grade")},
// 				{fieldname:'department', fieldtype:'Link', options: 'Department', label: __('Department')},
// 				{fieldname:'designation', fieldtype:'Link', options: 'Designation', label: __('Designation')},
// 				{fieldname:"employee", fieldtype: "Link", options: "Employee", label: __("Employee")},
// 				{fieldname:"payroll_payable_account", fieldtype: "Link", options: "Account", filters: {"company": frm.doc.company, "root_type": "Liability", "is_group": 0, "account_currency": frm.doc.currency}, label: __("Payroll Payable Account")},
// 				{fieldname:'base_variable', fieldtype:'Section Break'},
// 				{fieldname:'from_date', fieldtype:'Date', label: __('From Date'), "reqd": 1},
// 				{fieldname:'income_tax_slab', fieldtype:'Link', label: __('Income Tax Slab'), options: 'Income Tax Slab'},
// 				{fieldname:'base_col_br', fieldtype:'Column Break'},
// 				{fieldname:'base', fieldtype:'Currency', label: __('Base')},
// 				{fieldname:'variable', fieldtype:'Currency', label: __('Variable')}
// 			],
// 			primary_action: function() {
// 				var data = d.get_values();
// 				delete data.company
// 				delete data.currency
// 				frappe.call({
// 					doc: frm.doc,
// 					method: "assign_salary_structure",
// 					args: data,
// 					callback: function(r) {
// 						if(!r.exc) {
// 							d.hide();
// 							frm.reload_doc();
// 						}
// 					}
// 				});
// 			},
// 			primary_action_label: __('Assign')
// 		});

// 		d.fields_dict.grade.df.onchange = function() {
// 			const grade = d.fields_dict.grade.value;
// 			if (grade) {
// 				frappe.db.get_value('Employee Grade', grade, 'default_base_pay')
// 					.then(({ message }) => {
// 						d.set_value('base', message.default_base_pay);
// 					});
// 			}
// 		};

// 		d.show();
// 	},

// 	salary_slip_based_on_timesheet: function(frm) {
// 		frm.trigger("toggle_fields")
// 	},

// 	preview_salary_slip: function(frm) {
// 		frappe.call({
// 			method: "hrms.payroll.doctype.salary_structure.salary_structure.get_employees",
// 			args: {
// 				salary_structure: frm.doc.name
// 			},
// 			callback: function(r) {
// 				var employees = r.message;
// 				if(!employees) return;
// 				if (employees.length == 1){
// 					frm.events.open_salary_slip(frm, employees[0]);
// 				} else {
// 						var d = new frappe.ui.Dialog({
// 						title: __("Preview Salary Slip"),
// 						fields: [
// 							{
// 								"label":__("Employee"),
// 								"fieldname":"employee",
// 								"fieldtype":"Select",
// 								"reqd": true,
// 								options: employees
// 							}, {
// 								fieldname:"fetch",
// 								"label":__("Show Salary Slip"),
// 								"fieldtype":"Button"
// 							}
// 						]
// 					});
// 					d.get_input("fetch").on("click", function() {
// 						var values = d.get_values();
// 						if(!values) return;
// 							frm.events.open_salary_slip(frm, values.employee)

// 					});
// 					d.show();
// 				}
// 			}
// 		});
// 	},

// 	open_salary_slip: function(frm, employee){
// 		var print_format = frm.doc.salary_slip_based_on_timesheet ? "Salary Slip based on Timesheet" : "Salary Slip Standard";
// 		frappe.call({
// 			method: "hrms.payroll.doctype.salary_structure.salary_structure.make_salary_slip",
// 			args: {
// 				source_name: frm.doc.name,
// 				employee: employee,
// 				as_print: 1,
// 				print_format: print_format,
// 				for_preview: 1
// 			},
// 			callback: function(r) {
// 				var new_window = window.open();
// 				new_window.document.write(r.message);
// 			}
// 		});
// 	},

// 	toggle_fields: function(frm) {
// 		frm.toggle_display(['salary_component', 'hour_rate'], frm.doc.salary_slip_based_on_timesheet);
// 		frm.toggle_reqd(['salary_component', 'hour_rate'], frm.doc.salary_slip_based_on_timesheet);
// 		frm.toggle_reqd(['payroll_frequency'], !frm.doc.salary_slip_based_on_timesheet);
// 	}
// });

// var calculate_others = function(doc){
// 	cur_frm.call({
// 		method: "update_salary_structure",
// 		doc: doc
// 	});
// }

// var validate_date = function(frm, cdt, cdn) {
// 	var doc = locals[cdt][cdn];
// 	if(doc.to_date && doc.from_date) {
// 		var from_date = frappe.datetime.str_to_obj(doc.from_date);
// 		var to_date = frappe.datetime.str_to_obj(doc.to_date);

// 		if(to_date < from_date) {
// 			frappe.model.set_value(cdt, cdn, "to_date", "");
// 			frappe.throw(__("From Date cannot be greater than To Date"));
// 		}
// 	}
// }


// cur_frm.cscript.amount = function(doc, cdt, cdn){
// 	calculate_totals(doc, cdt, cdn);
// };

// var calculate_totals = function(doc) {
// 	var tbl1 = doc.earnings || [];
// 	var tbl2 = doc.deductions || [];

// 	var total_earn = 0; var total_ded = 0;
// 	for(var i = 0; i < tbl1.length; i++){
// 		total_earn += flt(tbl1[i].amount);
// 	}
// 	for(var j = 0; j < tbl2.length; j++){
// 		total_ded += flt(tbl2[j].amount);
// 	}
// 	doc.total_earning = total_earn;
// 	doc.total_deduction = total_ded;
// 	doc.net_pay = 0.0
// 	if(doc.salary_slip_based_on_timesheet == 0){
// 		doc.net_pay = flt(total_earn) - flt(total_ded);
// 	}

// 	refresh_many(['total_earning', 'total_deduction', 'net_pay']);
// }

// cur_frm.cscript.validate = function(doc, cdt, cdn) {
// 	calculate_totals(doc);
// }


// frappe.ui.form.on('Salary Detail', {
// 	amount: function(frm) {
// 		calculate_totals(frm.doc);
// 	},

// 	earnings_remove: function(frm) {
// 		calculate_totals(frm.doc);
// 	},

// 	deductions_remove: function(frm) {
// 		calculate_totals(frm.doc);
// 	},

// 	salary_component: function(frm, cdt, cdn) {
// 		var child = locals[cdt][cdn];
// 		if(child.salary_component){
// 			frappe.call({
// 				method: "frappe.client.get",
// 				args: {
// 					doctype: "Salary Component",
// 					name: child.salary_component
// 				},
// 				callback: function(data) {
// 					if(data.message){
// 						var result = data.message;
// 						frappe.model.set_value(cdt, cdn, 'condition', result.condition);
// 						frappe.model.set_value(cdt, cdn, 'amount_based_on_formula', result.amount_based_on_formula);
// 						if(result.amount_based_on_formula == 1){
// 							frappe.model.set_value(cdt, cdn, 'formula', result.formula);
// 						}
// 						else{
// 							frappe.model.set_value(cdt, cdn, 'amount', result.amount);
// 						}
// 						frappe.model.set_value(cdt, cdn, 'statistical_component', result.statistical_component);
// 						frappe.model.set_value(cdt, cdn, 'depends_on_payment_days', result.depends_on_payment_days);
// 						frappe.model.set_value(cdt, cdn, 'do_not_include_in_total', result.do_not_include_in_total);
// 						frappe.model.set_value(cdt, cdn, 'variable_based_on_taxable_salary', result.variable_based_on_taxable_salary);
// 						frappe.model.set_value(cdt, cdn, 'is_tax_applicable', result.is_tax_applicable);
// 						frappe.model.set_value(cdt, cdn, 'is_flexible_benefit', result.is_flexible_benefit);
// 						refresh_field("earnings");
// 						refresh_field("deductions");
// 					}
// 				}
// 			});
// 		}
// 	},

// 	amount_based_on_formula: function(frm, cdt, cdn) {
// 		var child = locals[cdt][cdn];
// 		if(child.amount_based_on_formula == 1){
// 			frappe.model.set_value(cdt, cdn, 'amount', null);
// 		}
// 		else{
// 			frappe.model.set_value(cdt, cdn, 'formula', null);
// 		}
// 	}
// })
