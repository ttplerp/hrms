// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Muster Roll Employee', {
	refresh: function(frm) {
		frm.set_query("unit", function() {
			return {
				"filters": {
					"is_unit": 1
				}
			};
		});
	},

	bank_branch: function(frm){
		frm.set_query("bank_branch", function(){
			return{
				"filters": {
					"financial_institution": frm.doc.bank_name
				}
			}
		})
	},

	rate_per_day: function(frm) {
		if(frm.doc.rate_per_day) {
			frm.set_value("rate_per_hour", (frm.doc.rate_per_day * 1.5) / 8)
			frm.refresh_field("rate_per_hour")
		}
	},
	
	cost_center: function(frm){
		if (!frm.doc.__islocal) {
			frm.set_value("date_of_transfer", frappe.datetime.nowdate());
			refresh_many("date_of_transfer");
			// validate_prev_doc(frm, __("Please select date of transfer to new cost center"));		
		}
	}
});

frappe.ui.form.on("Muster Roll Employee", "refresh", function(frm) {
    frm.set_query("cost_center", function() {
        return {
            "filters": {
				"is_group": 0,
				"is_disabled": 0
            }
        };
    });
})

// function validate_prev_doc(frm, title){
// 	return frappe.call({
// 		method: "erpnext.custom_utils.get_prev_doc",
// 		args: {doctype: frm.doctype, docname: frm.docname, col_list: "cost_center"},
// 		callback: function(r) {
// 			if(frm.doc.cost_center && (frm.doc.cost_center !== r.message.cost_center)){
// 				frappe.prompt({
// 					fieldtype: "Date",
// 					fieldname: "date_of_transfer",
// 					reqd: 1,
// 					description: __("*This information shall be recorded in employee internal work history.")},
// 					function(data) {
// 						frm.set_value("date_of_transfer", data.date_of_transfer);
// 						refresh_many("date_of_transfer");
// 					},
// 					title, 
// 					__("Update")
// 				);
// 			}
// 		}
// 	});
// }

// frappe.ui.form.on('Musterroll', {
// 	"rate_per_day": function(frm, cdt ,cdn) {
// 	var wages =locals[cdt][cdn];
// 	if(wages.rate_per_day) {
// 		frappe.model.set_value(wages.doctype, wages.name, "rate_per_hour", (wages.rate_per_day * 1.5) /8 );
// 		frm.refresh_field("rate_per_hour")
// 		}
// 	},
// })

