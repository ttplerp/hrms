// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Advance Settlement', {
    onload: (frm) => {
        frm.set_query("item_code", "items", function(doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            return {
                filters: {
                    "item_group": row.item_group
                }
            };
        });
    },
    
    setup: function(frm){
        if (frm.doc.employee && frm.doc.__islocal){
            frappe.call({
                method: "get_advance_details",
                doc: frm.doc,
                callback: function(r){
                    frm.refresh_field("total_deductible_amount")
                    frm.refresh_field("total_deducted_amount")
                    frm.refresh_field("balance_amount")
                    frm.refresh_field("settlement_amount")
                }
            })
        }
    },

    refresh: function(frm) {
        if(frm.doc.docstatus === 1){
            frm.add_custom_button(__('View General Ledger'), function() {
                frappe.route_options = {
                    "voucher_no": frm.doc.name,
                    "from_date": frm.doc.posting_date,
                    "to_date": frm.doc.posting_date,
                    "company": frm.doc.company,
                    "group_by_voucher": 0
                };
                frappe.set_route("query-report", "General Ledger");
            });
        }
        
        frm.fields_dict.items.grid.get_field("account").get_query = function(doc) {
            return {
                filters: {
                    "is_group": 0
                }
            };
        }
    },
    
    tds_percent: function(frm){
        frappe.call({
            method: "get_tds_account",
            doc: frm.doc,
            callback: function(r){
                if(r.message){
                    frm.set_value("tds_account", r.message);
                }
            }
        })
        frm.refresh_field("tds_account");
    },
    
    advance_type: function(frm){
        frappe.call({
            method: "get_credit_account",
            doc: frm.doc,
            callback: function(r){
                if(r.message){
                    frm.set_value("credit_account", r.message);
                }
            }
        })
        frm.refresh_field("tds_account");
    },
    
    edit_posting_date: function(frm){
        frm.set_df_property('posting_date','read_only', !frm.doc.edit_posting_date)
    },

    expense_branch: function(frm) {
        set_branch_child(frm);
        frappe.call({
            method: "get_cost_center",
            doc: frm.doc,
            callback: function (r) {
                frm.doc.items.forEach(e => {
                    e.cost_center = r.message;
                })
            }
        })
        frm.refresh_field('items')
    },
    
    taxes_and_charges: function(frm) {
        // Auto fetch GST details when taxes_and_charges is selected
        if (frm.doc.taxes_and_charges && frm.doc.apply_gst) {
            frappe.call({
                method: "get_gst_details_from_template",
                doc: frm.doc,
                callback: function(r) {
                    if (r.message) {
                        // Set all GST related fields
                        frm.set_value("gst_account", r.message.gst_account);
                        frm.set_value("gst_amount", r.message.gst_amount);
                        frm.refresh_field("gst_account");
                        frm.refresh_field("gst_amount");
                        
                        // Show message to user
                        if (r.message.gst_account) {
                            frappe.show_alert({
                                message: __("GST account and rate auto-fetched from tax template"),
                                indicator: 'green'
                            }, 5);
                        } else {
                            frappe.show_alert({
                                message: __("No GST account found in the selected tax template"),
                                indicator: 'orange'
                            }, 5);
                        }
                    }
                }
            });
        } else {
            // Clear GST fields if no tax template selected
            frm.set_value("gst_account", null);
            frm.set_value("gst_amount", 0);
            frm.refresh_field("gst_account");
            frm.refresh_field("gst_amount");
        }
    },
    
    apply_gst: function(frm) {
        if (frm.doc.apply_gst) {
            // If GST is checked, trigger taxes_and_charges change to fetch details
            frm.trigger("taxes_and_charges");
        } else {
            // Clear all GST fields if GST is unchecked
            frm.set_value("gst_account", null);
            frm.set_value("gst_amount", 0);
            frm.set_value("taxes_and_charges", null);
            frm.refresh_field("gst_account");
            frm.refresh_field("gst_amount");
            frm.refresh_field("taxes_and_charges");
        }
    },
    
    settlement_amount: function(frm) {
        // Recalculate GST when settlement amount changes
        if (frm.doc.apply_gst) {
            var gst_amount = flt(frm.doc.settlement_amount) * ( 5/ 100);
            frm.set_value("gst_amount", gst_amount);
            frm.refresh_field("gst_amount");
        }
    }
});

frappe.ui.form.on('Employee Advance Settlement Item', {
    item_code:function(frm,cdt,cdn){
        update_expense_account(frm, cdt, cdn);
    }
})

var update_expense_account = function(frm, cdt, cdn){
    let row = locals[cdt][cdn];
    if(row.item_code){
        frappe.call({
            method: "hrms.hr.doctype.employee_advance_settlement.employee_advance_settlement.get_expense_account",
            args: {
                "company": frm.doc.company,
                "item": row.item_code,
            },
            callback: function(r){
                frappe.model.set_value(cdt, cdn, "account", r.message);
                cur_frm.refresh_field(cdt, cdn, "account");
            }
        })
    }
}

var set_branch_child = function (frm) {
    frm.doc.items.forEach(el => {
        el.branch = frm.doc.expense_branch;
    });
    frm.refresh_field('items')
}