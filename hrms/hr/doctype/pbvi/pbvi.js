// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('PBVI', {
	setup: function(frm) {
		frm.get_docfield("items").allow_bulk_edit = 1;
	},
	
	refresh: function(frm) {
		if(!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today())
		}

		if(frm.doc.docstatus == 1) {
			if(frappe.model.can_read("Journal Entry")) {
				cur_frm.add_custom_button('Bank Entries', function() {
					frappe.route_options = {
						"Journal Entry Account.reference_type": frm.doc.doctype,
						"Journal Entry Account.reference_name": frm.doc.name,
					};
					frappe.set_route("List", "Journal Entry");
				}, __("View"));
			}
		}
	},
	"get_pbva": function(frm) {
		if(frm.doc.fiscal_year) {
			cur_frm.set_value("total_amount", 0.0);
			cur_frm.set_value("tax_amount", 0.0);
			cur_frm.set_value("net_amount", 0.0);
			refresh_many(["items", "total_amount", "tax_amount", "net_amount"]);
			//load_accounts(frm.doc.company)
			return frappe.call({
				method: "get_pbvi_details",
				doc: frm.doc,
				callback: function(r, rt) {
					frm.refresh_field("items");
					console.log(frm.doc.items)
					frm.refresh_fields();
				},
				freeze: true,
				freeze_message: "Loading Details..... Please Wait"
			});

			
		}
		else {
			msgprint("Select Fiscal Year First")
		}
		/*if(frm.doc.fiscal_year) {
			process_pbva(frm.doc.fiscal_year, frm);
		}
		else {
			msgprint("Select Fiscal Year First")
		}*/
	}

});

function process_pbva(fiscal_year, frm) {
	frappe.call({
		method: "get_pbva_details",
		args: {"fiscal_year": fiscal_year},
		callback: function(r) {
			if(r.message) {
				var total_amount = 0;
				var total_tax = 0;
				cur_frm.clear_table("items");

				r.message.forEach(function(pbva) {
				    var row = frappe.model.add_child(cur_frm.doc, "PBVI Details", "items");
					row.employee = pbva['employee']
					row.employee_name = pbva['employee_name']
					row.branch = pbva['branch']
					row.basic_pay = pbva['amount']
					/*if (calculate_pbva_percent(row.employee) == "above") {
						row.percent = frm.doc.above
					}
					else {
						row.percent = frm.doc.below
					} 
					row.amount = flt(row.basic_pay) * (flt(row.percent) / 100) * flt(row.months)*/
					row.amount = 0 
					row.tax_amount = calculate_tax(flt(row.amount))
					row.balance_amount = flt(row.amount) - flt(row.tax_amount)
					refresh_field("items");

					total_tax += row.tax_amount
					total_amount += row.amount
				});

				cur_frm.set_value("total_amount", total_amount)
				cur_frm.set_value("tax_amount", total_tax)
			}
		}
	})
}

frappe.ui.form.on("PBVI Details", { 
	//  "percent": function(frm, cdt, cdn) {
	//  	calculate_total(frm,cdt,cdn)
	//  },
	//  "months": function(frm, cdt, cdn) {
	//  	calculate_total(frm,cdt,cdn)
	// }, 
	"amount": function(frm, cdt, cdn) {
		calculate_total(frm,cdt,cdn)
	},
}),

function calculate_total(frm, cdt, cdn) {
	var item = locals[cdt][cdn]
	// item.amount = flt(item.basic_pay) * (flt(item.percent) / 100) * flt(item.months)
	item.tax_amount = calculate_tax(flt(item.amount))
	item.balance_amount = item.amount - item.tax_amount
	var total = 0;
	var total_tax = 0;
	var net   = 0.0;
	frm.doc.items.forEach(function(d) {
		total     += parseFloat(d.amount);
		total_tax += parseFloat(d.tax_amount);
		net       += parseFloat(d.amount-d.tax_amount);
	})
	cur_frm.set_value("total_amount", total);
	cur_frm.set_value("tax_amount", total_tax);
	cur_frm.set_value("net_amount", net);
	
	refresh_many(["items", "total_amount", "tax_amount", "net_amount"]);
}

function calculate_tax(gross_amt) {
	var tds_amount = 0;
	cur_frm.call({
		method: "hrms.hr.hr_custom_functions.get_salary_tax",
		args: { "gross_amt": gross_amt, },
		async: false,
		callback: function(r) {
			if(r.message) {
				tds_amount = Math.round(r.message);
			}
		}
	})
	return tds_amount;
}
