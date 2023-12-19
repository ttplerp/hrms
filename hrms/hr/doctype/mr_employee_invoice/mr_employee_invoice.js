// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('MR Employee Invoice', {
	refresh: function(frm) {
        if(frm.doc.docstatus===1){
			frm.add_custom_button(__('Ledger'), function(){
				frappe.route_options = {
                    voucher_no: frm.doc.name,
                    from_date: frm.doc.posting_date,
                    to_date: frm.doc.posting_date,
                    company: frm.doc.company,
                    group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			},__('View'));
            if (frm.doc.outstanding_amount>0){
                cur_frm.add_custom_button(__('Make Journal Entry'), function(doc) {
                    frm.events.make_journal_entry(frm)
                },__('Create'))
            }
        }
	},
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
    make_journal_entry:function(frm){
		frappe.call({
			method:"post_journal_entry",
			doc : frm.doc,
			callback: function (r) {
				
			},
		});
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
