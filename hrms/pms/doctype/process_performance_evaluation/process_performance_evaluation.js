// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Process Performance Evaluation', {
	onload: function (frm) {
		if (!frm.doc.posting_date) {
			frm.doc.posting_date = frappe.datetime.nowdate();
		}
	},

	refresh: function(frm) {
		if (frm.doc.docstatus == 0) {
			frm.set_intro("");
			if (!frm.is_new() && !frm.doc.performacne_evaluation_created) {
				frm.page.clear_actions_menu();
				frm.page.clear_primary_action();
				if (!frm.doc.successful){
					frm.page.add_action_item(__("Get Employees"),
						function() {
							frm.events.get_employee_details(frm);
						}
					);

					frm.page.add_action_item(__("Get MR Employees"),
						function() {
							frm.events.get_mr_employee_details(frm);
						}
					);
				}
				if ((frm.doc.employees || []).length || (frm.doc.mr_employees || []).length) {
					frm.page.add_action_item(__('Create Performance Evaluation'), function() {
						frm.events.create_performance_evaluation(frm);
					});
				}
			}
			else if(frm.doc.performance_evaluation_created){
				frm.page.clear_actions_menu();
				frm.page.clear_primary_action();
				// if(!frm.doc.salary_slips_submitted){
					// Submit salary slips
					frm.page.add_action_item(__('Submit PPE'), function() {
						frm.save('Submit').then(()=>{
							frm.page.clear_actions_menu();
							frm.page.clear_primary_action();
							frm.refresh();
							frm.events.refresh(frm);
						});
					});
				// }
			}
		} else {
			cur_frm.page.clear_actions();
		}
	},

	get_employee_details: function (frm) {
		frm.set_value("number_of_employees", 0);
		frm.refresh_field("number_of_employees")
		return frappe.call({
			doc: frm.doc,
			method: 'get_employee_details',
			callback: function (r) {
				if (r.message) {
					frm.set_value("number_of_employees", r.message);
					frm.refresh_field("number_of_employees");
					frm.refresh_field("employees");
					frm.dirty();
				}
			},
			freeze: true,
			freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Fetching Employee Records...</span>'
		});
	},

	get_mr_employee_details: function (frm) {
		frm.set_value("number_of_mr_employees", 0);
		frm.refresh_field("number_of_mr_employees")
		return frappe.call({
			doc: frm.doc,
			method: 'get_mr_employee_details',
			callback: function (r) {
				if (r.message) {
					frm.set_value("number_of_mr_employees", r.message);
					frm.refresh_field("number_of_mr_employees");
					frm.refresh_field("mr_employees");
					frm.dirty();
				}
			},
			freeze: true,
			freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Fetching MR Employee Records...</span>'
		});
	},

	create_performance_evaluation: function (frm) {
		frm.call({
			doc: frm.doc,
			method: "create_performance_evaluation",
			callback: function (r) {
				frm.refresh();
				frm.toolbar.refresh();
			},
			freeze: true,
			freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Creating Performance Evaluation...</span>'
		})
	},
});
