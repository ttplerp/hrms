// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Travel Authorization'] = {
	add_fields: ["employee_name", "employee", "grade", "docstatus", "document_status", "travel_claim"],
	has_indicator_for_draft: 1,
	get_indicator: function(doc) {
		if(doc.docstatus==0) {
			if(doc.document_status == 'Rejected') {
				return ["Authorization Rejected", "red", "document_status,=,Rejected"];
			}
			else {
				return ["Authorization Draft", "orange", "docstatus,=,0|document_status,not like,Rejected"];
			}
		}

		if(doc.docstatus == 1) {
			if(doc.travel_claim) {
				return ["Claimed", "green", "docstatus,=,1|travel_claim,>,0"];
			}
			else {
				return ["Approved", "blue", "docstatus,=,1"];
			}
		}

		if(doc.docstatus == 2) {
			return ["Cancelled", "red", "docstatus,=,2"];
		}
	}
};
