// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Training Event', {
	budget_projected: function(frm) {
        frm.trigger('calculate_difference');
    },
    actual_expense: function(frm) {
        frm.trigger('calculate_difference');
    },

    calculate_difference: function(frm) {
        // Convert values to numbers
        let projected = parseFloat(frm.doc.budget_projected) || 0;
        let actual = parseFloat(frm.doc.actual_expense) || 0;

        // Calculate difference
        let diff = projected - actual;

        // Set value in difference field
        frm.set_value('difference', diff);
    },
	employees_on_form_rendered: function (frm) {
        calculate_employee_totals(frm);
    },

    employees_add: function (frm) {
        calculate_employee_totals(frm);
    },

    employees_remove: function (frm) {
        calculate_employee_totals(frm);
    },
	onload_post_render: function (frm) {
		frm.get_field("employees").grid.set_multiple_add("employee");
	},
	refresh: function (frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Training Result"), function () {
				frappe.route_options = {
					training_event: frm.doc.name
				};
				frappe.set_route("List", "Training Result");
			});
			frm.add_custom_button(__("Training Feedback"), function () {
				frappe.route_options = {
					training_event: frm.doc.name
				};
				frappe.set_route("List", "Training Feedback");
			});
		}
        if (frm.doc.employees) {
            frm.doc.employees.forEach(function(row) {
                calculate_row_total(frm, row.doctype, row.name);
            });
        }
		frm.events.set_employee_query(frm);
		toggle_employee_cost_fields(frm);
        
        frm.set_query("travel_claim", "employees", function (doc, cdt, cdn) {
            let row = locals[cdt][cdn];

            if (!row.employee) {
                return {};
            }

            return {
                filters: {
                    employee: row.employee
                },
                order_by: "creation desc"
            };
        });
	},
	ex_country_in_country(frm) {
        toggle_employee_cost_fields(frm);
    },

	set_employee_query: function(frm) {
		let emp = [];
		for (let d in frm.doc.employees) {
			if (frm.doc.employees[d].employee) {
				emp.push(frm.doc.employees[d].employee);
			}
		}
		frm.set_query("employee", "employees", function () {
			return {
				filters: {
					name: ["NOT IN", emp],
					status: ["in", ["Active", "Left"]]
				}
			};
		});
	}
});

frappe.ui.form.on("Training Event Employee", {
	employee: function(frm) {
		frm.events.set_employee_query(frm);
	},
    course_fee: calculate_row_total,
	air_fare: calculate_row_total,
	travel_insurance: calculate_row_total,
	dsa_incidental_and_mileage: calculate_row_total,
	mileage: calculate_row_total,
	// create_travel_request: function(frm, cdt, cdn){
	// 	var item = locals[cdt][cdn];
	// 	// Follwoing line temporarily replaced by SHIV on 2020/09/17, need to restore back
	// 	if (frm.doc.docstatus == 1 && (item.travel_request == '' || item.travel_request == undefined)) {
	// 			frappe.flags.employee = item.employee;
	// 			frappe.model.open_mapped_doc({
	// 				method: "hrms.hr.doctype.training_event.training_event.create_travel_request",
	// 				frm: cur_frm,
	// 				args: {"employee": item.employee, "child_ref": item.name}
	// 			})
	// 	}
	// },
	total: function (frm, cdt, cdn) {
        calculate_employee_totals(frm);
    },

    employees_remove: function (frm) {
        calculate_employee_totals(frm);
    },
    
});

function calculate_employee_totals(frm) {
    let total_amount = 0;
    let employee_count = 0;

    if (frm.doc.employees) {
        employee_count = frm.doc.employees.length;

        frm.doc.employees.forEach(row => {
            total_amount += flt(row.total);
        });
    }

    frm.set_value('no_of_employee', employee_count);
    frm.set_value('grand_total', total_amount);
}

function toggle_employee_cost_fields(frm) {
    const is_in_country = frm.doc.ex_country_in_country === "In-Country";

    const grid = frm.fields_dict.employees.grid;

    // Ex-Country only fields
    const ex_country_fields = [
        "air_fare",
        "travel_insurance",
        "mileage"
    ];

    // In-Country & Ex-Country fields
    const common_fields = [
        "course_fee",
        "dsa_incidental_and_mileage",
        "total"
    ];

    // Toggle Ex-Country-only fields
    ex_country_fields.forEach(field => {
        grid.update_docfield_property(field, "hidden", is_in_country);
    });

    // Always show common fields
    common_fields.forEach(field => {
        grid.update_docfield_property(field, "hidden", false);
    });

    frm.refresh_field("employees");
}

function calculate_row_total(frm, cdt, cdn) {
	let row = locals[cdt][cdn];

	let total =
		flt(row.course_fee) +
		flt(row.air_fare) +
		flt(row.travel_insurance) +
		flt(row.dsa_incidental_and_mileage) +
		flt(row.mileage);

	frappe.model.set_value(cdt, cdn, "total", total);

	// update parent total
	calculate_employee_totals(frm);
}