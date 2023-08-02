// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('MR Employee Invoice', {
	
    onload:function(frm){
        frm.set_query("credit_account",function(doc){
            return {
                filters:{
                    is_group:0,
                    company:frm.doc.company
                }
            }
        })
    },
    get_attendance:function(frm){
        if (frm.doc.docstatus != 1){
            frappe.call({
                method:"get_attendance",
                doc:frm.doc,
                callback:function(r){
                    frm.refresh_field("attendance")
                    frm.refresh_field("total_days_worked")
                    frm.dirty()
                }
            })
        }
    },
    get_ot:function(frm){
        if (frm.doc.docstatus != 1){
            frappe.call({
                method:"get_ot",
                doc:frm.doc,
                callback:function(r){
                    frm.refresh_field("ot")
                    frm.refresh_field("total_ot_hrs")
                    frm.dirty()
                }
            })
        }
    },
    fiscal_year:function(frm){
        frm.events.reset_child_tables(frm)
    },
    mr_employee:function(frm){
        frm.events.reset_child_tables(frm)
    },
    month:function(frm){
        frm.events.reset_child_tables(frm)
    },
    reset_child_tables:function(frm){
		frm.clear_table("deduction");
        frm.refresh_field("deduction")
		frm.clear_table("ot");
        frm.refresh_field("ot")
        frm.clear_table("attendance")
        frm.refresh_field("attendance")
	},
});
