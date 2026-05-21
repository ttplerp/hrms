// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Desuup', {
	// refresh: function(frm) {

	// }
	onload: function(frm) {
		frm.set_query('bank_branch', function(doc) {
			return {
				filters: {
					"financial_institution": doc.bank_name
				}
			};
		});

		frm.set_query("dzongkhag", function(){
			return {
				filters: {
					'country_name': frm.doc.country,
					'disabled': 0,
				}
			}
		})

		frm.set_query("gewog", function(){
			return {
				filters: {
					'dzongkhag': frm.doc.dzongkhag,
					'disabled': 0,
				}
			}
		})

		frm.set_query("village", function(){
			return {
				filters: {
					'gewog': frm.doc.gewog,
					'disabled': 0,
				}
			}
		})

		frm.set_query("present_dzongkhag", function(){
			return {
				filters: {
					'country_name': frm.doc.present_country,
					'disabled': 0,
				}
			}
		})

		frm.set_query("present_gewog", function(){
			return {
				filters: {
					'dzongkhag': frm.doc.present_dzongkhag,
					'disabled': 0,
				}
			}
		})
	},
	create_user: function(frm) {
		if (!frm.doc.email_id) {
			frappe.throw(__("Please enter Preferred Contact Email"));
		}
		frappe.call({
			method: "hrms.hr.doctype.desuup.desuup.create_user",
			args: {
				desuup: frm.doc.name,
				email: frm.doc.email_id
			},
			callback: function (r) {
				frm.set_value("user_id", r.message);
			}
		});
	}
});
