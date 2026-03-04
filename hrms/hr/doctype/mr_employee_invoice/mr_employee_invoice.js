// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('MR Employee Invoice', {
    refresh: function (frm) {
        if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Ledger'), function(){
                frappe.route_options = {
                    voucher_no: frm.doc.name,
                    from_date: frm.doc.posting_date,
                    to_date: frm.doc.posting_date,
                    company: frm.doc.company,
                    group_by_voucher: false
                };
                frappe.set_route("query-report", "General Ledger");
            }, __('View'));
        }
        
        // Make salary tax field read-only
        frm.fields_dict.salary_tax.read_only = 1;
    },
    
    onload: function(frm) {
        frm.set_query("credit_account", function() {
            return {
                filters: {
                    is_group: 0,
                    company: frm.doc.company
                }
            };
        });
    },
    
    get_attendance: function(frm) {
        if (frm.doc.docstatus != 1) {
            frappe.call({
                method: "get_attendance",
                doc: frm.doc,
                callback: function(r) {
                    frm.refresh_field("attendance");
                    frm.refresh_field("total_days_worked");
                    frm.dirty();
                }
            });
        }
    },
    
    get_ot: function(frm) {
        if (frm.doc.docstatus != 1) {
            frappe.call({
                method: "get_ot",
                doc: frm.doc,
                callback: function(r) {
                    frm.refresh_field("ot");
                    frm.refresh_field("total_ot_hrs");
                    frm.dirty();
                }
            });
        }
    },
    
    tds_percent: function(frm) {
        if (frm.doc.tds_percent) {
            frappe.call({
                method: "erpnext.accounts.utils.get_tds_account",
                args: {
                    percent: frm.doc.tds_percent,
                    company: frm.doc.company
                },
                callback: function(r) {
                    if(r.message) {
                        frm.set_value("tds_account", r.message);
                        frm.refresh_fields("tds_account");
                    }
                }
            });
        }
    },
    
    fiscal_year: function(frm) {
        frm.events.reset_child_tables(frm);
    },
    
    mr_employee: function(frm) {
        frm.events.reset_child_tables(frm);
    },
    
    month: function(frm) {
        frm.events.reset_child_tables(frm);
    },
    
    reset_child_tables: function(frm) {
        frm.clear_table("deductions");
        frm.refresh_field("deductions");
        frm.clear_table("ot");
        frm.refresh_field("ot");
        frm.clear_table("attendance");
        frm.refresh_field("attendance");
    },
    
    // Recalculate when any amount field changes
    attendance_add: function(frm, cdt, cdn) {
        frm.events.calculate_totals(frm);
    },
    
    ot_add: function(frm, cdt, cdn) {
        frm.events.calculate_totals(frm);
    },
    
    calculate_totals: function(frm) {
        // Trigger server-side calculation
        frm.save_or_update().then(() => {
            frm.refresh();
        });
    }
});