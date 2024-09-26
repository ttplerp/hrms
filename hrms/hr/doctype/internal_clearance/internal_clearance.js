// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Internal Clearance', {

	refresh: function (frm) {
		if(frm.doc.mail_sent==0 &&  !frm.doc.__islocal){
			frm.add_custom_button(__('Send Email'), function () {
				
				let arr={'icthr': frm.doc.icthr[0][0], 'ictcr':frm.doc.ictcr[0][0], 'iad':frm.doc.iad[0][0], 'afd':frm.doc.afd[0][0]}
	
				frappe.call({
					method: "hrms.hr.doctype.internal_clearance.internal_clearance.sendemail",
					args: {
						emails: arr,
						purpose: frm.doc.purpose,
						uname: frm.doc.employee_name,
						designation: frm.doc.designation,
						branch: frm.doc.branch,
					},
					callback: function(r) {
						console.log(r);
					}
				});

				frappe.call({
					method: "hrms.hr.doctype.internal_clearance.internal_clearance.setemailcheck", //dotted path to server method
					args: {
						docid: frm.doc.name,
					},
					callback: function(r) {
						//console.log(r);
					}
				});

				frm.refresh_fields();
				frm.reload_doc(); 
				frm.reload_doc();

	
				
			});
			
		}else{
			frm.remove_custom_button(__('Send Email'));
			
		}
        

		
    }
});
