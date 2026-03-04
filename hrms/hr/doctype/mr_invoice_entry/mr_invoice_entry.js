// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('MR Invoice Entry', {
    refresh: function(frm) {
        if(frm.doc.docstatus == 0 && frm.doc.mr_invoice_created == 0){
            cur_frm.add_custom_button(__('Get MR Employee'), function() {
                frm.events.get_mr_employee(frm);
            }, __("Create"));
            
            if (!frm.doc.__islocal){
                cur_frm.add_custom_button(__('Create MR Invoice'), function() {
                    frm.events.create_mr_invoice(frm);
                }, __("Create"));
            }
        }
        
        if(frm.doc.docstatus == 1 && frm.doc.mr_invoice_submit == 1 && frm.doc.status !== "Paid"){
            cur_frm.add_custom_button(__('Post To Account'), function() {
                frm.events.post_to_account(frm);
            }, __("Create"));
        }
        
        // Set field queries
        frm.set_query("mr_employee", "deductions", function() {
            return {
                filters: {
                    branch: frm.doc.branch
                }
            };
        });
        
        frm.fields_dict.deductions.grid.get_field("account").get_query = function() {
            return {
                filters: {
                    "is_group": 0
                }
            };
        };
        
        frm.fields_dict.arrears_and_allownace.grid.get_field("account").get_query = function() {
            return {
                filters: {
                    "is_group": 0
                }
            };
        };
        
        frm.fields_dict.items.grid.get_field("salary_tax").read_only = 1;
        frm.fields_dict.items.grid.get_field("net_payable_amount").read_only = 1;
    },
    
    create_mr_invoice: function(frm) {
        frappe.call({
            method: "create_mr_invoice",
            doc: frm.doc,
            freeze: true,
            freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Creating MR Invoice.....</span>'
        }).then(r => {
            cur_frm.reload_doc();
        }).fail(error => {
            console.error("Error creating MR invoices:", error);
            frappe.msgprint(__("Error creating MR invoices. Please check the error log."));
        });
    },
    
    post_to_account: function(frm) {
        frappe.call({
            method: "post_to_account",
            doc: frm.doc,
            callback: function(r) {
                cur_frm.reload_doc();
            },
            freeze: true,
            freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Posting To account.....</span>'
        });
    },
    
    get_mr_employee: function(frm) {
        frappe.call({
            method: "get_mr_employee",
            doc: frm.doc,
            callback: function(r) {
                frm.refresh_field("items");
                frm.dirty();
            }
        });
    },
    
    branch: function(frm) {
        frm.set_query("mr_employee", "deductions", function() {
            return {
                filters: {
                    branch: frm.doc.branch
                }
            };
        });
        
        frm.clear_table("items");
        frm.clear_table("deductions");
        frm.clear_table("advances");
        frm.refresh_fields();
    },
    
    get_advance: function(frm) {
        frappe.call({
            method: "get_advance",
            doc: frm.doc,
            callback: function(r) {
                frm.refresh_field("advances");
                frm.dirty();
            }
        });
    },
    
    // Calculate totals when items change
    items_add: function(frm, cdt, cdn) {
        frm.events.calculate_totals(frm);
    },
    
    items_remove: function(frm, cdt, cdn) {
        frm.events.calculate_totals(frm);
    },
    
    calculate_totals: function(frm) {
        let total_grand_total = 0;
        let total_salary_tax = 0;
        let total_net_payable = 0;
        
        $.each(frm.doc.items || [], function(i, item) {
            let grand_total = flt(item.grand_total) || 0;
            let salary_tax = flt(grand_total * 0.15);
            let net_payable = flt(grand_total - salary_tax);
            
            // Update the row
            frappe.model.set_value(item.doctype, item.name, 'salary_tax', salary_tax);
            frappe.model.set_value(item.doctype, item.name, 'net_payable_amount', net_payable);
            
            total_grand_total += grand_total;
            total_salary_tax += salary_tax;
            total_net_payable += net_payable;
        });
        
        // Update main totals
        frm.set_value('total_grand_total', flt(total_grand_total));
        frm.set_value('total_salary_tax', flt(total_salary_tax));
        frm.set_value('total_net_payable_amount', flt(total_net_payable));
        
        frm.refresh_field('items');
    }
});

// Field level events for items table
frappe.ui.form.on('MR Invoice Entry Item', {
    grand_total: function(frm, cdt, cdn) {
        var item = locals[cdt][cdn];
        let salary_tax = flt(flt(item.grand_total) * 0.15);
        let net_payable = flt(flt(item.grand_total) - salary_tax);
        
        frappe.model.set_value(cdt, cdn, 'salary_tax', salary_tax);
        frappe.model.set_value(cdt, cdn, 'net_payable_amount', net_payable);
        
        frm.events.calculate_totals(frm);
    },
    
    salary_tax: function(frm, cdt, cdn) {
        // Recalculate net payable if salary tax is manually changed
        var item = locals[cdt][cdn];
        let net_payable = flt(flt(item.grand_total) - flt(item.salary_tax));
        frappe.model.set_value(cdt, cdn, 'net_payable_amount', net_payable);
        frm.events.calculate_totals(frm);
    }
});