// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Separation Clearance', {
	refresh: function(frm) {
		if(frm.doc.mail_sent == 0 && frm.doc.approvers_set == 1){
			frm.add_custom_button(__('Apply'), () => {
				frappe.call({
					method: "apply",
					doc: frm.doc,
					callback: function(r){
						console.log(r.message)
						let alert_dialog = new frappe.ui.Dialog({
							title: String(r.message),
							primary_action: values => {
								alert_dialog.disable_primary_action();
								window.location.reload()
							},
							primary_action_label: 'OK'
						});
						alert_dialog.show();
					}
			})
			}, __('Action'));
		}
	},
	onload: function(frm){
		if(frm.doc.approvers_set == 0){
			frappe.call({
				method: "set_approvers",
				doc:frm.doc,
				callback: function(r){
					frm.refresh_fields();
				}
			})
		}
	},
});
