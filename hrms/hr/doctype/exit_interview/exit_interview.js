// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exit Interview', {
	// refresh: function(frm) {
	// 	get_job_satisfaction(frm)
	// 	get_management(frm)
	// 	get_remuneration_benefits(frm)
	// 	get_the_company(frm)
	// 	get_supervisor(frm)
	// },
	onload: function (frm) {
		if (frm.doc.__islocal) {
			get_questions(frm)
			get_job_satisfaction(frm)
			get_management(frm)
			get_remuneration_benefits(frm)
			get_the_company(frm)
			get_supervisor(frm)
		} 
	},
});

frappe.ui.form.on('Job Satisfaction', {
	strongly_agree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.strongly_agree==1){
			row.agree = 0;
			row.disagree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("job_satisfaction")
		}
	},
	agree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.agree==1){
			row.strongly_agree = 0;
			row.disagree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("job_satisfaction")
		}
	},
	disagree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.disagree==1){
			row.agree = 0;
			row.strongly_agree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("job_satisfaction")
		}
	},
	strongly_disagree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.strongly_disagree==1){
			row.agree = 0;
			row.disagree = 0;
			row.strongly_agree = 0;
			frm.refresh_field("job_satisfaction")
		}
	}
});
frappe.ui.form.on('Management', {
	strongly_agree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.strongly_agree==1){
			row.agree = 0;
			row.disagree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("management")
		}
	},
	agree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.agree==1){
			row.strongly_agree = 0;
			row.disagree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("management")
		}
	},
	disagree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.disagree==1){
			row.agree = 0;
			row.strongly_agree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("management")
		}
	},
	strongly_disagree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.strongly_disagree==1){
			row.agree = 0;
			row.disagree = 0;
			row.strongly_agree = 0;
			frm.refresh_field("management")
		}
	}
});
frappe.ui.form.on('Remuneration Benefits', {
	strongly_agree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.strongly_agree==1){
			row.agree = 0;
			row.disagree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("remuneration_benefits")
		}
	},
	agree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.agree==1){
			row.strongly_agree = 0;
			row.disagree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("remuneration_benefits")
		}
	},
	disagree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.disagree==1){
			row.agree = 0;
			row.strongly_agree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("remuneration_benefits")
		}
	},
	strongly_disagree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.strongly_disagree==1){
			row.agree = 0;
			row.disagree = 0;
			row.strongly_agree = 0;
			frm.refresh_field("remuneration_benefits")
		}
	}
});
frappe.ui.form.on('The Company', {
	strongly_agree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.strongly_agree==1){
			row.agree = 0;
			row.disagree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("the_company")
		}
	},
	agree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.agree==1){
			row.strongly_agree = 0;
			row.disagree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("the_company")
		}
	},
	disagree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.disagree==1){
			row.agree = 0;
			row.strongly_agree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("the_company")
		}
	},
	strongly_disagree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.strongly_disagree==1){
			row.agree = 0;
			row.disagree = 0;
			row.strongly_agree = 0;
			frm.refresh_field("the_company")
		}
	}
});
frappe.ui.form.on('Supervisor', {
	strongly_agree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.strongly_agree==1){
			row.agree = 0;
			row.disagree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("supervisor")
		}
	},
	agree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.agree==1){
			row.strongly_agree = 0;
			row.disagree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("supervisor")
		}
	},
	disagree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.disagree==1){
			row.agree = 0;
			row.strongly_agree = 0;
			row.strongly_disagree = 0;
			frm.refresh_field("supervisor")
		}
	},
	strongly_disagree: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if(row.strongly_disagree==1){
			row.agree = 0;
			row.disagree = 0;
			row.strongly_agree = 0;
			frm.refresh_field("supervisor")
		}
	}
});
var get_questions = (frm)=>{
		frappe.call({
			method: "get_questions",
			doc: frm.doc,
			callback: (r)=> {
				cur_frm.refresh_field("job_satisfaction")
				cur_frm.refresh_field("management")
				cur_frm.refresh_field("remuneration_benefits")
				cur_frm.refresh_field("the_company")
				cur_frm.refresh_field("supervisor")
			}
		})
	// }else{
	// 	frappe.throw("Select Part iii to get <b>Job Satisfaction</b>")
	// }
}
