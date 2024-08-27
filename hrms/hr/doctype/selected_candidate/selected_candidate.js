// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Selected Candidate', {
	refresh: function (frm) {

	},
	get_selected_list: function (frm) {
		if (frm.doc.posting_date) {
			get_selected_list(frm)
		}
	}
});

frappe.ui.form.on("Selected List", {
	create_employee: function (frm, cdt, cdn) {
		var child = frappe.get_doc(cdt, cdn);
		if (child.user_id != null) {
			console.log(child.user_id)
			frappe.model.open_mapped_doc({
				method: "hrms.hr.doctype.selected_candidate.selected_candidate.create_employee",	
				frm: cur_frm,
				args: {
					"user_id": child.user_id,
					"child_name": child.name
				}
			});
			
		}else{
			frappe.msgprint("No userId")
		}
	},
});

var get_selected_list = (frm)=>{
	frappe.call({
		method: 'get_selected_list',
		doc: frm.doc,
		callback: (r)=> {
			frm.refresh_field("selected_list")
		},
		freeze: true,
		freeze_message: "Fetching selected candidate list.... Please Wait",
	})
}
