// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Advance', {
	setup: function(frm) {
		frm.add_fetch("employee", "company", "company");
		if (frm.doc.advance_type == "Travel Advance"){
			frm.add_fetch("company", "default_employee_advance_account", "advance_account");
		}else{
			frm.add_fetch("company", "travel_advance_account", "advance_account");
		}
		frm.set_query("employee", function() {
			return {
				filters: {
					"status": "Active"
				}
			};
		});

		frm.set_query("advance_account", function() {
			if (!frm.doc.employee) {
				frappe.msgprint(__("Please select employee first"));
			}
			let company_currency = erpnext.get_currency(frm.doc.company);
			let currencies = [company_currency];
			if (frm.doc.currency && (frm.doc.currency != company_currency)) {
				currencies.push(frm.doc.currency);
			}

			return {
				filters: {
					"root_type": "Asset",
					"is_group": 0,
					"company": frm.doc.company,
					"account_currency": ["in", currencies],
				}
			};
		});

		frm.set_query('salary_component', function() {
			return {
				filters: {
					"type": "Deduction"
				}
			};
		});

		frm.set_query("reference", function() {
			return {
				filters: {
					"employee": frm.doc.employee
				}
			};
		});
	},

	refresh: function(frm) {
		if(frm.doc.employee){
			frappe.call({
				method:"validate_employment_status",
				doc: frm.doc
			})
		}
		// commanted by rinzin on 4/01/2023
		// if (frm.doc.docstatus === 1 &&
		// 	(flt(frm.doc.paid_amount) < flt(frm.doc.advance_amount)) &&
		// 	frappe.model.can_create("Payment Entry")) {
		// 	frm.add_custom_button(__('Payment'),
		// 		function () {
		// 			frm.events.make_payment_entry(frm);
		// 		}, __('Create'));
		// } 
		if (
			frm.doc.docstatus === 1 &&
			frm.doc.advance_type === "Imprest Advance" &&
			flt(frm.doc.claimed_amount) < flt(frm.doc.paid_amount) - flt(frm.doc.return_amount) &&
			frappe.model.can_create("Expense Claim")
		) {
			frm.add_custom_button(
				__("Expense Claim"),
				function () {
					frm.events.make_expense_claim(frm);
				},
				__('Create')
			);
		}
		if (
			frm.doc.docstatus === 1
			&& (flt(frm.doc.claimed_amount) < flt(frm.doc.paid_amount) - flt(frm.doc.return_amount))
		) {
			if (frm.doc.repay_unclaimed_amount_from_salary == 0 && frappe.model.can_create("Journal Entry")) {
				frm.add_custom_button(__("Return"), function() {
					frm.trigger('make_return_entry');
				}, __('Create'));
			} else if (frm.doc.repay_unclaimed_amount_from_salary == 1 && frappe.model.can_create("Additional Salary")) {
				frm.add_custom_button(__("Deduction from Salary"), function() {
					frm.events.make_deduction_via_additional_salary(frm);
				}, __('Create'));
			}
		}
	},

	make_deduction_via_additional_salary: function(frm) {
		frappe.call({
			method: "hrms.hr.doctype.employee_advance.employee_advance.create_return_through_additional_salary",
			args: {
				doc: frm.doc
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	// commanted by rinzin on 4/01/2023
	// make_payment_entry: function(frm) {
	// 	let method = "hrms.overrides.employee_payment_entry.get_payment_entry_for_employee";
	// 	if (frm.doc.__onload && frm.doc.__onload.make_payment_via_journal_entry) {
	// 		method = "hrms.hr.doctype.employee_advance.employee_advance.make_bank_entry";
	// 	}
	// 	return frappe.call({
	// 		method: method,
	// 		args: {
	// 			"dt": frm.doc.doctype,
	// 			"dn": frm.doc.name
	// 		},
	// 		callback: function(r) {
	// 			var doclist = frappe.model.sync(r.message);
	// 			frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
	// 		}
	// 	});
	// },

	make_expense_claim: function(frm) {
		return frappe.call({
			method: "hrms.hr.doctype.expense_claim.expense_claim.get_expense_claim",
			args: {
				"employee_name": frm.doc.employee,
				"company": frm.doc.company,
				"employee_advance_name": frm.doc.name,
				"posting_date": frm.doc.posting_date,
				"paid_amount": frm.doc.paid_amount,
				"claimed_amount": frm.doc.claimed_amount,
				"advance_type":frm.doc.advance_type,
			},
			callback: function(r) {
				const doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	make_return_entry: function(frm) {
		frappe.call({
			method: 'hrms.hr.doctype.employee_advance.employee_advance.make_return_entry',
			args: {
				'employee': frm.doc.employee,
				'company': frm.doc.company,
				'employee_advance_name': frm.doc.name,
				'return_amount': flt(frm.doc.paid_amount - frm.doc.claimed_amount),
				'advance_account': frm.doc.advance_account,
				'mode_of_payment': frm.doc.mode_of_payment,
				'currency': frm.doc.currency,
				'exchange_rate': frm.doc.exchange_rate
			},
			callback: function(r) {
				const doclist = frappe.model.sync(r.message);
				frappe.set_route('Form', doclist[0].doctype, doclist[0].name);
			}
		});
	},

	employee: function(frm, cdt, cdn) {
		if (frm.doc.employee) {
			frappe.call({
				method:"validate_employment_status",
				doc: frm.doc
			})
			frappe.run_serially([
				() => frm.trigger('get_pending_amount'),
				() => frm.trigger('set_pay_details'),
				() => frm.trigger('set_recovery_start_date'),
				//() => frm.trigger('get_accumulated_advance_amount_from_employee_advance')
			]);
		}
	},
	advance_type: function(frm, cdt, cdn) {
		if (frm.doc.employee) {
			frappe.call({
				method:"validate_employment_status",
				doc: frm.doc
			})
			frappe.run_serially([
				() => frm.trigger('get_accumulated_advance_amount_from_employee_advance'),
				frm.set_value("reference_type", frm.doc.advance_type == "Travel Advance" ? "Travel Request" : null)
			]);

		}
		frappe.call({
			method: "hrms.hr.doctype.employee_advance.employee_advance.select_account",
			args: {
				"advance_type": frm.doc.advance_type,
				"company": frm.doc.company
			},
			callback: function(r) {
				frm.set_value("advance_account", r.message);
				frm.refresh_field("advance_account");
			}
		});
	},

	// advance_amount: function(frm){
	// 	if (frm.doc.advance_type == "Salary Advance"){
	// 		frappe.call({
	// 			method: "validate_advance_amount",
	// 			doc: frm.doc,
	// 			callback: function(r){
	// 				frm.refresh_field("advance_amount");
	// 				frm.refresh_field("recovery_start_date");
	// 				frm.refresh_field("recovery_end_date");
	// 				frm.refresh_field("monthly_deduction");
	// 			}
	// 		})
	// 	}
	// },
	
	advance_amount: function (frm) {
		if (frm.doc.advance_type === "Salary Advance" || frm.doc.advance_type === "Employee Loan" ) { 
			calculate_monthly_deduction(frm)
		}
	},

	deduction_month: function (frm) {
		if (frm.doc.advance_type === "Salary Advance" || frm.doc.advance_type === "Employee Loan" ) { 
			calculate_monthly_deduction(frm)
		}
		if (frm.doc.deduction_month) { 
			frappe.call({
				method: "hrms.hr.doctype.employee_advance.employee_advance.calculate_recovery_end_date",
				args: {
					"start_date": frm.doc.recovery_start_date,
					"months": frm.doc.deduction_month
				},callback: function(r) {
					console.log(r.message)
					frm.set_value("recovery_end_date", r.message);
				}
			});
		}
	},

	recovery_start_date: function (frm) {
		if (frm.doc.advance_type === "Salary Advance" || frm.doc.advance_type === "Employee Loan" ) { 
			calculate_monthly_deduction(frm)
		}
		if (frm.doc.deduction_month) { 
			frappe.call({
				method: "hrms.hr.doctype.employee_advance.employee_advance.calculate_recovery_end_date",
				args: {
					"start_date": frm.doc.recovery_start_date,
					"months": frm.doc.deduction_month
				},callback: function(r) {
					console.log(r.message)
					frm.set_value("recovery_end_date", r.message);
				}
			});
		}
	},

	// deduction_month: function(frm){
	// 	frappe.call({
	// 		method: "validate_deduction_month",
	// 		doc: frm.doc,
	// 		callback: function(r){
	// 			frm.refresh_field("deduction_month");
	// 			frm.refresh_field("recovery_start_date");
	// 			frm.refresh_field("recovery_end_date");
	// 			frm.refresh_field("monthly_deduction");
				
	// 		}
	// 	})
	// },

	set_recovery_start_date: function (frm) { 
		frm.set_value("recovery_start_date", frm.doc.posting_date);
	},

	set_pay_details: function(frm){
		frappe.call({
			method: "set_pay_details",
			doc: frm.doc,
			callback: function(r){
				frm.refresh_field("basic_pay");
				frm.refresh_field("net_pay");
				frm.refresh_field("deduction_month");
				frm.refresh_field("max_advance_limit");
				frm.refresh_field("monthly_deduction");
			}
		})
	},

	get_accumulated_advance_amount_from_employee_advance: function(frm){
		frappe.call({
			method: "get_accumulated_advance_amount",
			doc: frm.doc,
			callback: function(r){
				frm.refresh_field("total_advance")
			}
		})
	},
	get_pending_amount: function(frm) {
		frappe.call({
			method: "hrms.hr.doctype.employee_advance.employee_advance.get_pending_amount",
			args: {
				"employee": frm.doc.employee,
				"posting_date": frm.doc.posting_date
			},
			callback: function(r) {
				frm.set_value("pending_amount", r.message);
			}
		});
	},

	get_employee_currency: function(frm) {
		frappe.call({
			method: "hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment.get_employee_currency",
			args: {
				employee: frm.doc.employee,
			},
			callback: function(r) {
				if (r.message) {
					frm.set_value('currency', r.message);
					frm.refresh_fields();
				}
			}
		});
	},

	currency: function(frm) {
		if (frm.doc.currency) {
			var from_currency = frm.doc.currency;
			var company_currency;
			if (!frm.doc.company) {
				company_currency = erpnext.get_currency(frappe.defaults.get_default("Company"));
			} else {
				company_currency = erpnext.get_currency(frm.doc.company);
			}
			if (from_currency != company_currency) {
				frm.events.set_exchange_rate(frm, from_currency, company_currency);
			} else {
				frm.set_value("exchange_rate", 1.0);
				frm.set_df_property('exchange_rate', 'hidden', 1);
				frm.set_df_property("exchange_rate", "description", "");
			}
			frm.refresh_fields();
		}
	},

	set_exchange_rate: function(frm, from_currency, company_currency) {
		frappe.call({
			method: "erpnext.setup.utils.get_exchange_rate",
			args: {
				from_currency: from_currency,
				to_currency: company_currency,
			},
			callback: function(r) {
				frm.set_value("exchange_rate", flt(r.message));
				frm.set_df_property('exchange_rate', 'hidden', 0);
				frm.set_df_property("exchange_rate", "description", "1 " + frm.doc.currency +
					" = [?] " + company_currency);
			}
		});
	},
	// advance_type: function(frm){
	// 	frm.set_value("reference_type", frm.doc.advance_type == "Travel Advance" ? "Travel Request" : null)
	// }
});

var calculate_monthly_deduction = function (frm) { 
	if (frm.doc.deduction_month > 0 && frm.doc.advance_amount > 0) { 
		const isDivisible = (frm.doc.advance_amount % frm.doc.deduction_month === 0)
		if (!isDivisible) {
			const monthly_amount = Math.ceil(flt(frm.doc.advance_amount / frm.doc.deduction_month))
			const new_advance = flt(frm.doc.deduction_month * monthly_amount)
			frappe.msgprint("Your advance amount is updated to " + new_advance + " in order to make it equally divisible by the no. of installments")
			frm.set_value("advance_amount", new_advance);
			frm.set_value("monthly_deduction", monthly_amount);
		} else { 
			const monthly_amount = flt(frm.doc.advance_amount / frm.doc.deduction_month)
			frm.set_value("monthly_deduction", monthly_amount);
		}
	}
}