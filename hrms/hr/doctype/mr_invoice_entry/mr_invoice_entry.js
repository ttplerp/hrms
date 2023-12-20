// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('MR Invoice Entry', {
	refresh: function(frm) {
        if(frm.doc.docstatus == 0 && frm.doc.mr_invoice_created == 0){
            cur_frm.add_custom_button(__('Get MR Employee'), function(doc) {
				frm.events.get_mr_employee(frm)
			},__("Create"))
            if (!frm.doc.__islocal){
                cur_frm.add_custom_button(__('Create MR Invoice'), function(doc) {
                    frm.events.create_mr_invoice(frm)
                },__("Create"))
            }
		}
        if(frm.doc.docstatus == 1 && frm.doc.mr_invoice_submit == 1){
            cur_frm.add_custom_button(__('Post To Account'), function(doc) {
				frm.events.post_to_account(frm)
			},__("Create"))
		}
        frm.set_query("mr_employee","deductions",function(doc){
            return {
                filters:{
                    branch:frm.doc.branch
                }
            }
        }),
        frm.fields_dict.deductions.grid.get_field("account").get_query = function(doc) {
            return {
                filters: {
                    "is_group": 0
                }
            };
        },
        frm.fields_dict.arrears_and_allownace.grid.get_field("account").get_query = function(doc) {
            return {
                filters: {
                    "is_group": 0
                }
            };
        }
	},
    create_mr_invoice:function(frm){
        frappe.call({
            method:"create_mr_invoice",
            doc:frm.doc,
            callback:function(r){
                cur_frm.reload_doc()
            },
            freeze: true,
            freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Creating MR Invoice.....</span>'
        })
    },
    post_to_account:function(frm){
        frappe.call({
            method:"post_to_account",
            doc:frm.doc,
            callback:function(r){
                cur_frm.reload_doc()
            },
            freeze: true,
            freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Posting To account.....</span>'
        
        })
    },
    get_mr_employee:function(frm){
        frappe.call({
            method:"get_mr_employee",
            doc:frm.doc,
            callback:function(r){
                frm.refresh_field("items")
                frm.dirty()
            }
        })
    },
    branch:function(frm){
        frm.set_query("mr_employee","deductions",function(doc){
            return {
                filters:{
                    branch:frm.doc.branch
                }
            }
        })
		frm.clear_table("items");
		frm.clear_table("deductions");
        frm.refresh_fields()
    },
    get_advance: function(frm) {
		frappe.call({
			method: "get_advance",
			doc: frm.doc,
			callback: function(r) {
				frm.refresh_field("advances")
                frm.dirty()
			}
		})
	}
});

// frappe.ui.form.on('MR Employee Deduction Entry', {
//     mr_employee: (frm, cdt, cdn) => {
//         var item = locals[cdt][cdn];
//         if (item.is_tds_deduction == 1) {
//             make_tds_details(frm, cdt, cdn)
//         }
//         frappe.call({
//             method: "check_mr_employee",
//             args: {"mr_employee": item.mr_employee},
//             doc: frm.doc
//         })
       
//     },
//     tds_percent: (frm, cdt, cdn) => {
//         make_tds_details(frm, cdt, cdn)
//     }, 
// });

// var make_tds_details =  function(frm, cdt, cdn) {
//     var item = locals[cdt][cdn];
//     frappe.call({
//         method: "get_tds_amount",
//         doc: frm.doc,
//         args: {"mr_employee": item.mr_employee, "tds_percent": item.tds_percent},
//         callback: function(r) {
//             console.log(r.message[0]);
//             frappe.model.set_value(cdt, cdn, 'amount', r.message[0]);
// 	        frm.refresh_field("amount", cdt, cdn)
//             frappe.model.set_value(cdt, cdn, 'account', r.message[1]);
// 	        frm.refresh_field("account", cdt, cdn)
//         }
//     })
// }
