// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
{% include "erpnext/public/js/controllers/accounts.js" %}

cur_frm.add_fetch('company', 'default_letter_head', 'letter_head');
cur_frm.add_fetch('employee', 'company', 'company');

frappe.ui.form.on('Salary Structure', {
	onload: function(frm, cdt, cdn){
		make_ed_table(frm);
	},
	onload_post_render: function(frm) {
		highlight_expired_components(frm);
	},
	refresh: function(frm, cdt, cdn) {
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
	eligible_for_food: function(frm){
		calculate_others(frm);
	},
	eligible_for_ita_allowance: function(frm){
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
	eligible_for_necessity_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_site_allowance: function(frm){
		calculate_others(frm);
	},
	eligible_for_other_deduction: function(frm){
		calculate_others(frm);
	},
	other_deduction: function(frm){
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
	fuel_allowances: function(frm){
		calculate_others(frm);
	},
	pda: function(frm){
		calculate_others(frm);
	},
	shift: function(frm){
		calculate_others(frm);
	},
	food: function(frm){
		calculate_others(frm);
	},
	necessity: function(frm){
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
	site_allowance: function(frm){
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
	food_method: function(frm){
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
	},
	necessity_method: function(frm){
		calculate_others(frm);
	},
	site_allowance_method: function(frm){
		calculate_others(frm);
	},
	// other_deduction_method: function(frm){
	// 	calculate_others(frm);
	// }
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

function calculate_others(frm) {
	frappe.call({
		method: "update_salary_structure",
		doc: frm.doc,
		args: {"remove_flag": 0},
		callback: function (r) {
			if(r.message){
				// earnings
				console.log(r.message)
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
