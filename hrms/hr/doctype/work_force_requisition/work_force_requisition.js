
frappe.ui.form.on('Work force Requisition', {
	refresh: function(frm) {
        if (frm.doc.requested_by) {
            fetch_approver(frm);
        }
    },
    requesting_branch: function(frm) {
        if (frm.doc.requesting_branch === "VCSC") {
            frm.set_value("request_from", "Corporate Office");
        } else {
            frm.set_value("request_from", "VCSC");
        }
    },
	requested_by: function(frm) {
        if (!frm.doc.requested_by) return;
        fetch_approver(frm);
    },
});

function fetch_approver(frm) {
    frappe.call({
        method: "hrms.hr.doctype.work_force_requisition.work_force_requisition.get_workforce_requisiton_approver",
        args: { user_id: frm.doc.requested_by }, 
        callback: function(r) {
            if (r.message) {
                frm.set_value("approver", r.message.approver);
                frm.set_value("approver_name", r.message.approver_name);
                frm.set_value("approver_designation", r.message.approver_designation);
            } else {
                frappe.msgprint("No approver found for this employee.");
            }
        }
    });
}
