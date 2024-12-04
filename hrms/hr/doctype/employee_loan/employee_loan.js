// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Loan', {
	refresh: function(frm) {
		refresh_html(frm);
	},
	onload: function (frm) {
	// 	frm.set_query("employee_loan_application", function () {
	// 		return {
	// 			"filters": {
	// 				"employee": frm.doc.employee,
	// 				"docstatus": 1,
	// 				"status": "Approved"
	// 			}
	// 		};
	// 	});

	// 	frm.set_query("interest_income_account", function () {
	// 		return {
	// 			"filters": {
	// 				"company": frm.doc.company,
	// 				"root_type": "Income",
	// 				"is_group": 0
	// 			}
	// 		};
	// 	});

		frm.set_query("employee", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"branch": frm.doc.branch,
				}
			};
		});

	// 	$.each(["payment_account", "employee_loan_account"], function (i, field) {
	// 		frm.set_query(field, function () {
	// 			return {
	// 				"filters": {
	// 					"company": frm.doc.company,
	// 					"root_type": "Asset",
	// 					"is_group": 0
	// 				}
	// 			};
	// 		});
	// 	})
	},

	// refresh: function (frm) {
	// 	if (frm.doc.docstatus == 1 && (frm.doc.status == "Sanctioned" || frm.doc.status == "Partially Disbursed")) {
	// 		frm.add_custom_button(__('Create Disbursement Entry'), function () {
	// 			frm.trigger("make_jv");
	// 		})
	// 	}
	// 	frm.trigger("toggle_fields");
	// },

	// make_jv: function (frm) {
	// 	frappe.call({
	// 		args: {
	// 			"employee_loan": frm.doc.name,
	// 			"company": frm.doc.company,
	// 			"employee_loan_account": frm.doc.employee_loan_account,
	// 			"employee": frm.doc.employee,
	// 			"loan_amount": frm.doc.loan_amount,
	// 			"payment_account": frm.doc.payment_account
	// 		},
	// 		method: "hrms.hr.doctype.employee_loan.employee_loan.make_jv_entry",
	// 		callback: function (r) {
	// 			if (r.message)
	// 				var doc = frappe.model.sync(r.message)[0];
	// 			frappe.set_route("Form", doc.doctype, doc.name);
	// 		}
	// 	})
	// },

	// mode_of_payment: function (frm) {
	// 	if (frm.doc.mode_of_payment && frm.doc.company) {
	// 		frappe.call({
	// 			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
	// 			args: {
	// 				"mode_of_payment": frm.doc.mode_of_payment,
	// 				"company": frm.doc.company
	// 			},
	// 			callback: function (r, rt) {
	// 				if (r.message) {
	// 					frm.set_value("payment_account", r.message.account);
	// 				}
	// 			}
	// 		});
	// 	}
	// },

	// employee_loan_application: function (frm) {
	//     if(frm.doc.employee_loan_application){
    //         return frappe.call({
    //             method: "hrms.hr.doctype.employee_loan.employee_loan.get_employee_loan_application",
    //             args: {
    //                 "employee_loan_application": frm.doc.employee_loan_application
    //             },
    //             callback: function (r) {
    //                 if (!r.exc && r.message) {
    //                     frm.set_value("loan_type", r.message.loan_type);
    //                     frm.set_value("loan_amount", r.message.loan_amount);
    //                     frm.set_value("repayment_method", r.message.repayment_method);
    //                     frm.set_value("monthly_repayment_amount", r.message.repayment_amount);
    //                     frm.set_value("repayment_periods", r.message.repayment_periods);
    //                     frm.set_value("rate_of_interest", r.message.rate_of_interest);
    //                 }
    //             }
    //         });
    //     }
	// },

	// repayment_method: function (frm) {
	// 	frm.trigger("toggle_fields")
	// },

	// toggle_fields: function (frm) {
	// 	frm.toggle_enable("monthly_repayment_amount", frm.doc.repayment_method == "Repay Fixed Amount per Period")
	// 	frm.toggle_enable("repayment_periods", frm.doc.repayment_method == "Repay Over Number of Periods")
	// },

	employee: function(frm) {
		frm.trigger('set_recovery_start_date')
	},

	set_recovery_start_date: function (frm) { 
		frm.set_value("recovery_start_date", frm.doc.posting_date);
	},

	loan_amount: function (frm) {
		calculate_monthly_deduction(frm);
	},

	installment_no: function (frm) {
		calculate_monthly_deduction(frm);
		if (frm.doc.installment_no) { 
			frappe.call({
				method: "hrms.hr.doctype.employee_loan.employee_loan.calculate_recovery_end_date",
				args: {
					"start_date": frm.doc.recovery_start_date,
					"months": frm.doc.installment_no
				},callback: function(r) {
					console.log(r.message)
					frm.set_value("recovery_end_date", r.message);
				}
			});
		}
	},

	recovery_start_date: function(frm) {
		if (frm.doc.installment_no) { 
			frappe.call({
				method: "hrms.hr.doctype.employee_loan.employee_loan.calculate_recovery_end_date",
				args: {
					"start_date": frm.doc.recovery_start_date,
					"months": frm.doc.installment_no
				},callback: function(r) {
					console.log(r.message)
					frm.set_value("recovery_end_date", r.message);
				}
			});
		}
	}
});

var calculate_monthly_deduction = function (frm) { 
	if (frm.doc.installment_no > 0 && frm.doc.loan_amount > 0) { 
		const isDivisible = (frm.doc.loan_amount % frm.doc.installment_no === 0)
		if (!isDivisible) {
			const monthly_amount = Math.ceil(flt(frm.doc.loan_amount / frm.doc.installment_no))
			const new_advance = flt(frm.doc.installment_no * monthly_amount)
			frappe.msgprint("Your advance amount is updated to " + new_advance + " in order to make it equally divisible by the no. of installments")
			frm.set_value("loan_amount", new_advance);
			frm.set_value("monthly_deduction", monthly_amount);
		} else { 
			const monthly_amount = flt(frm.doc.loan_amount / frm.doc.installment_no)
			frm.set_value("monthly_deduction", monthly_amount);
		}
	}
}

var refresh_html = function(frm){
	var journal_entry_status = "";
	if(frm.doc.journal_entry_status){
		journal_entry_status = '<div style="font-style: italic; font-size: 0.8em; ">* '+frm.doc.journal_entry_status+'</div>';
	}
	
	if(frm.doc.journal_entry){
		$(cur_frm.fields_dict.journal_entry_html.wrapper).html('<label class="control-label" style="padding-right: 0px;">Journal Entry</label><br><b>'+'<a href="/desk/Form/Journal Entry/'+frm.doc.journal_entry+'">'+frm.doc.journal_entry+"</a> "+"</b>"+journal_entry_status);
	}	
}