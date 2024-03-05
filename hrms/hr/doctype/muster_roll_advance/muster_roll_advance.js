// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Muster Roll Advance', {
	refresh: function(frm) {
		refresh_html(frm);

		frm.set_query("mr_employee", function(doc){
            return {
                filters:{
                    branch:frm.doc.branch,
                    muster_roll_group:frm.doc.muster_roll_group,
                }
            }
        }),

		frm.fields_dict.items.grid.get_field("mr_employee").get_query = function(doc) {
            return {
                filters: {
                    "branch": frm.doc.branch,
					"muster_roll_group": frm.doc.muster_roll_group,
                }
            };
        }
	},

	muster_roll_group: function(frm) {
		frappe.call({
			method: "get_advance_account",
			doc: frm.doc,
			callback: function (r) {
				frm.set_value('advance_account', r.message);
				frm.refresh_fields();
			}
		})
	},

	get_mr_employee: function(frm) {
		frappe.call({
            method:"get_mr_employee",
            doc:frm.doc,
            callback:function(r){
                frm.refresh_field("items")
                frm.dirty()
            }
        })
	}
});

var refresh_html = function(frm){
	var journal_entry_status = "";
	if(frm.doc.journal_entry_status){
		journal_entry_status = '<div style="font-style: italic; font-size: 0.8em; ">* '+frm.doc.journal_entry_status+'</div>';
	}
	
	if(frm.doc.journal_entry){
		$(cur_frm.fields_dict.journal_entry_html.wrapper).html('<label class="control-label" style="padding-right: 0px;">Journal Entry</label><br><b>'+'<a href="/desk/Form/Journal Entry/'+frm.doc.journal_entry+'">'+frm.doc.journal_entry+"</a> "+"</b>"+journal_entry_status);
	}	
}
