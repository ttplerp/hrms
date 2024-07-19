frappe.ready(function() {
	frappe.web_form.on('did', (field, did) => {
		if(did.length > 7){
			frappe.web_form.on('cid_number',(field, cid) => {
				if(cid.length === 11){
					frappe.web_form.on('date_of_birth',(field, dob) => {
						populate_detail(did, cid, dob);
					});
				}
			});
		}
	});
});

function populate_detail(did, cid, dob){
	frappe.call({
		//method: 'erpnext.rental_management.doctype.api_setting.api_setting.get_cid_detail',
		method: 'hrms.hr.doctype.update_bank_account.update_bank_account.get_detail',
		args: {
			did: did,
			cid: cid,
			dob: dob,
		},
		callback: function(r) {
			if(r.message){
				//console.log(r.message['email_id']);
				$('[data-fieldname="desuup_name"]').val(r.message['desuup_name']); //Name
				$('[data-fieldname="gender"]').val(r.message['gender']); //Gender
				$('[data-fieldname="email_id"]').val(r.message['email_id']); //Email
				$('[data-fieldname="mobile_number"]').val(r.message['mobile_number']); //Mobile No
				$('[data-fieldname="bank_name"]').val(r.message['bank_name']); // Bank
				$('[data-fieldname="bank_account_number"]').val(r.message['bank_account_number']); // Bank Branch
				$('[data-fieldname="bank_account_type"]').val(r.message['bank_account_type']); // Bank Account Type	
				$('[data-fieldname="bank_branch"]').val(r.message['bank_branch']); // Bank Account No
			}
			else{
				frappe.throw("Details like CID and DOB are mismatching. Please provide correct info to UPDATE!")
			}
			/*
			if(r.message['middleName']){
				var applicant_name = r.message['firstName'] + " " + r.message['middleName'] + " " + r.message['lastName'];
			}
			else{
				var applicant_name = r.message['firstName'] + " " + r.message['lastName'];
			}
			
			//Handle the response from the server
			if(r.message) {
				$('[data-fieldname="application_name"]').val(applicant_name);		
			}else{
				frappe.throw("No such CID details found")
			}*/
		},
	});
}