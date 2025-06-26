// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work force Requisition', {
	requesting_branch: function(frm){
	
		if (frm.doc.requesting_branch === "VCSC"){
			frm.set_value("from_branch", "Corporate Office");
		}
		else{
			frm.set_value("from_branch","VCSC")
		}

	}
});
