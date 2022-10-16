// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Leave Travel Concession', {
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
	"get_ltc": function(frm) {
		if(frm.doc.fiscal_year) {
			//load_accounts(frm.doc.company)
			return frappe.call({
				method: "get_ltc_details",
				doc: frm.doc,
				callback: function(r, rt) {
					frm.refresh_field("items");
					frm.refresh_fields();
				},
				freeze: true,
				freeze_message: "Loading Employee Details..... Please Wait"
			});
		}
		else {
			msgprint("Select Fiscal Year First")
		}
	}
});

function process_ltc(branch) {
	frappe.call({
		method: "hrms.hr.doctype.leave_travel_concession.leave_travel_concession.get_ltc_details",
		args: {"branch": branch},
		callback: function(r) {
			if(r.message) {
				var total_amount = 0;
				cur_frm.clear_table("items");

				r.message.forEach(function(ltc) {
				        var row = frappe.model.add_child(cur_frm.doc, "LTC Details", "items");
					row.employee = ltc['employee']
					row.employee_name = ltc['employee_name']
					row.branch = ltc['branch']
					if (ltc['amount'] > 15000){
						row.amount = 15000
					}
					else {
						row.amount = ltc['amount']
					}
					refresh_field("items");

					total_amount += row.amount
				});

				cur_frm.set_value("total_amount", total_amount)
			}
			else {
				msgprint("No employee record found for the selected branch")
			}
		}
	})
}

frappe.ui.form.on("LTC Details", "amount", function(frm, cdt, cdn) {
	var total = 0;
	frm.doc.items.forEach(function(d) {
		total += d.amount
	})
	cur_frm.set_value("total_amount", total)
})


