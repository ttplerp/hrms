// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Separation Clearance', {
	refresh: function(frm) {
		frappe.call({
			method: "check_logged_in_user_role",
			doc:frm.doc,
			callback: function(r){
				console.log(r.message)
				toggle_remarks_display(frm, r.message[0], r.message[1], r.message[2], r.message[3])
			}
		})
		// if(frm.doc.mail_sent == 0 && frm.doc.approvers_set == 1){
		// 	frm.add_custom_button(__('Apply'), () => {
		// 		frappe.call({
		// 			method: "apply",
		// 			doc: frm.doc,
		// 			callback: function(r){
		// 				console.log(r.message)
		// 				let alert_dialog = new frappe.ui.Dialog({
		// 					title: String(r.message),
		// 					primary_action: values => {
		// 						alert_dialog.disable_primary_action();
		// 						window.location.reload()
		// 					},
		// 					primary_action_label: 'OK'
		// 				});
		// 				alert_dialog.show();
		// 			}
		// 	})
		// 	}, __('Action'));
		// }
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

var toggle_remarks_display = function(frm, fa, ita, iaa, hsa){
	frm.set_df_property("fa_remarks","read_only",fa);
	frm.set_df_property("fa_clearance","read_only",fa);
	frm.set_df_property("ita_remarks","read_only",ita);
	frm.set_df_property("ita_clearance","read_only",ita);
	frm.set_df_property("iaa_remarks","read_only",iaa);
	frm.set_df_property("iaa_clearance","read_only",iaa);
	frm.set_df_property("hsa_remarks","read_only",hsa);
	frm.set_df_property("hsa_clearance","read_only",hsa);

	frm.set_df_property("document_no","read_only",frappe.user.has_role(["HR User"]) != true);
}