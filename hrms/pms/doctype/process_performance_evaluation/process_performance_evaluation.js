// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Process Performance Evaluation', {
	onload: function (frm) {
		if (!frm.doc.posting_date) {
			frm.doc.posting_date = frappe.datetime.nowdate();
		}
	},

	refresh: function(frm) {
		if(frm.doc.docstatus == 0 && frm.doc.performance_evaluation_created == 0){
            cur_frm.add_custom_button(__('Get Employee'), function(doc) {
				frm.events.get_employee_details(frm)
			},__("Create"))
			cur_frm.add_custom_button(__('Get MR Employee'), function(doc) {
				frm.events.get_mr_employee_details(frm)
			},__("Create"))
			
		}
		if (!frm.doc.__islocal && frm.doc.docstatus == 1 && (((frm.doc.employees || []).length || (frm.doc.mr_employees || []).length))){
			cur_frm.add_custom_button(__('Create Performance Evaluation'), function(doc) {
				frm.events.create_performance_evaluation(frm)
			},__("Create"))
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

frappe.ui.form.on("PPE MR Employee Detail", { 
	mr_employees_remove: function (frm) {
		cal_total_employee(frm)
	}
});
frappe.ui.form.on("PPE Employee Detail", { 
	employees_remove: function (frm) {
		cal_total_employee(frm)
	}
});

function cal_total_employee(frm){
	let total_count = 0

	if (frm.doc.employees){
		frm.doc.employees.map(item => {
			total_count += 1
		})
	}
	cur_frm.set_value('number_of_employees', total_count)
	cur_frm.refresh_field('number_of_employees')
}

function cal_total_mr_employee(frm){
	let total_count = 0

	if (frm.doc.mr_employees){
		frm.doc.mr_employees.map(item => {
			total_count += 1
		})
	}
	cur_frm.set_value('number_of_mr_employees', total_count)
	cur_frm.refresh_field('number_of_mr_employees')
}