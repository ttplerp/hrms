// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bonus', {
	setup: function(frm) {
		frm.get_docfield("items").allow_bulk_edit = 1;
		// Following coded added by SHIV on 31/10/2017
		frm.get_field('items').grid.editable_fields = [
			{fieldname: 'employee_name', columns: 2},
			{fieldname: 'basic_pay', columns: 2},
			{fieldname: 'amount', columns: 2},
			{fieldname: 'tax_amount', columns: 2},
			{fieldname: 'balance_amount', columns: 2}
		];
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
	"get_employees": function(frm) {
		if(frm.doc.fiscal_year) {
			cur_frm.set_value("total_amount", 0.0);
			cur_frm.set_value("tax_amount", 0.0);
			cur_frm.set_value("net_amount", 0.0);
			refresh_many(["items", "total_amount", "tax_amount", "net_amount"]);
			
			//load_accounts(frm.doc.company)
			return frappe.call({
				method: "get_employees",
				doc: frm.doc,
				callback: function(r, rt) {
					frm.refresh_field("items");
					frm.refresh_fields();
				},
				freeze: true,
                                freeze_message: "Loading Details..... Please Wait"
			});
		}
		else {
			msgprint("Select Fiscal Year First")
		}
	}

});

frappe.ui.form.on("Bonus Details", { 
	/*"percent": function(frm, cdt, cdn) {
		calculate_total(frm,cdt,cdn)
	},
	"months": function(frm, cdt, cdn) {
		calculate_total(frm,cdt,cdn)
	}, */
	"amount": function(frm, cdt, cdn) {
		calculate_total(frm,cdt,cdn)
	},
})

function calculate_total(frm, cdt, cdn) {
	var item = locals[cdt][cdn]
	//item.amount = flt(item.basic_pay) * (flt(item.percent) / 100) * flt(item.months)
	item.tax_amount = calculate_tax(flt(item.amount))
	item.balance_amount = item.amount - item.tax_amount
	var total     = 0.0;
	var total_tax = 0.0;
	var net       = 0.0;
	frm.doc.items.forEach(function(d) {
		total     += parseFloat(d.amount);
		total_tax += parseFloat(d.tax_amount);
		net       += parseFloat(d.amount-d.tax_amount)
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