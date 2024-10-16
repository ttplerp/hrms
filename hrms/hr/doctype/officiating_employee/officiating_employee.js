// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Officiating Employee', {
	refresh: function(frm) {
		if(frm.doc.to_date < get_today) {
			/*cur_frm.add_custom_button(__('Revoke Permissions'), this.revoke_permission)
			frm.add_custom_button("Create Job Card", function() {
				return frappe.call({
					method: "erpnext.hr.doctype.officiating_employee.officiating_employee.revoke_perm",
					args: {frm: cur_frm},
					callback: function(r) {}
				})
			});*/
		}
	},
	onload: function(frm) {
		if(!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today())
		}
		//cur_frm.fields_dict.officiate.$input.autocomplete("disable");
	},
	from_date: function(frm) {
		if(frm.doc.from_date && frm.doc.to_date && frm.doc.to_date < frm.doc.from_date) {
			cur_frm.set_vaue("from_date", "")
			cur_frm.refresh_field("from_date")
			frappe.msgprint("To Date cannot be smaller than from date")
		}
	},
	to_date: function(frm) {
		if(frm.doc.from_date && frm.doc.to_date && frm.doc.to_date < frm.doc.from_date) {
			cur_frm.set_vaue("to_date", "")
			cur_frm.refresh_field("to_date")
			frappe.msgprint("To Date cannot be smaller than from date")
		}
	},
	employee: function(frm){
		frappe.call({
			method: "get_roles",
			doc: frm.doc,
			callback: function(r){
				frm.refresh_field("roles");
			}
		})
	},
	officiate: function(frm){
		console.log(frm.doc.employee)
		frappe.call({
			method: "get_roles",
			doc: frm.doc,
			callback: function(r){
				frm.refresh_field("roles");
			}
		})
	},
	/*validate: function(frm) {
		if(frm.doc.employee) {
			return frappe.call({
				method: "validate",
				doc: frm.doc,
				callback: function(r, rt) {
					frm.refresh_field("items");
					frm.refresh_fields();
				}
			});
		}
	},*/
	"revoke_permission": function(frm) {
		return frappe.call({
			method: "revoke_perm",
			doc: frm.doc,
			callback: function(r, rt) {
			}
		})	
	}
});

cur_frm.add_fetch("employee", "employee_name", "employee_name")
cur_frm.add_fetch("officiate", "employee_name", "officiate_name")
