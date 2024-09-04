// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dispatch', {
	department: function(frm) {
        if(frm.doc.department) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Dispatch Format",
                    filters: { "department": frm.doc.department },
                    fieldname: "dispatch_format"
                },
                callback: function(r) {
					console.log(r.message)
                    if (r.message) {
                        frm.set_value("dispatch_format", r.message.dispatch_format);
                        frm.refresh_field("dispatch_format");
                    }
                }
            });

            // Reapply the filter when the department is changed
            frm.set_query('dispatch_format', function() {
                return {
                    filters: {
                        'department': frm.doc.department
                    }
                };
            });
        }
    },
	dispatch_type: function(frm) {
        // Make dispatch_format read-only when dispatch_type is "Out Going"
        frm.toggle_enable('dispatch_number', frm.doc.dispatch_type !== 'Out Going');
    },

    refresh: function(frm) {
        // Ensure the field is set correctly on load
        frm.trigger('dispatch_type');
    }
















	
});

