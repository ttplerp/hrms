// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Performance Evaluation', {
	onload_post_render: function (frm) {
		$(".grid-add-row").addClass('hidden');
		get_competency(frm);
		get_evaluators(frm);
		get_start_end_date(frm);
	},

	onload: function (frm) {
		if (frappe.session.user == frm.doc.eval_1_user_id) {
			frappe.meta.get_docfield("Evaluate Competency Item", "evaluator_1" , frm.doc.name).in_list_view = 1;
			frappe.meta.get_docfield("Evaluate Competency Item", "evaluator_1" , frm.doc.name).reqd = 1;
		} else if (frappe.session.user == frm.doc.eval_2_user_id) {
			frappe.meta.get_docfield("Evaluate Competency Item", "evaluator_2" , frm.doc.name).in_list_view = 1;
			frappe.meta.get_docfield("Evaluate Competency Item", "evaluator_2" , frm.doc.name).reqd = 1;
		} else if (frappe.session.user == frm.doc.eval_3_user_id) {
			frappe.meta.get_docfield("Evaluate Competency Item", "evaluator_3" , frm.doc.name).in_list_view = 1;
			frappe.meta.get_docfield("Evaluate Competency Item", "evaluator_3" , frm.doc.name).reqd = 1;
		}	
	},

	// refresh: function(frm) {
	
	// },

	employee: (frm) => {
		get_evaluators(frm);
	},

	employee_group: (frm) => {
		get_competency(frm)
	},
	month: (frm) => {
		get_start_end_date(frm);
	},
	evaluator_1_score: (frm) => {
		cal_final_score(frm)
	},
	evaluator_2_score: (frm) => {
		cal_final_score(frm)
	},
	evaluator_3_score: (frm) => {
		cal_final_score(frm)
	}
});


frappe.ui.form.on('Evaluate Competency Item', {
	onload:(frm, cdt, cdn)=>{
		toggle_display(frm, cdt, cdn)
		setRemarksReqd(frm);
	},
	refresh:(frm, cdt, cdn)=>{
		toggle_display(frm, cdt, cdn)
	},
	evaluator_1: function(frm, cdt, cdn) {
		// var row = locals[cdt][cdn];
		// // frm.toggle_display(['inr_bank_code', 'inr_purpose_code'], (row.bank_name === 'INR'));
		// frm.toggle_reqd(['eval_1_remarks'], (row.evaluator_1 <= 1));
		// frm.refresh_fields(['eval_1_remarks']);
		cal_eval_total(frm)
		setRemarksReqdForCurrentRow(frm, cdt, cdn);
	},
	evaluator_2: function(frm) {
		cal_eval_total(frm)
	},
	evaluator_3: function(frm) {
		cal_eval_total(frm)
	},
});

function setRemarksReqd(frm) {
    frm.doc.evaluate_competency_items.forEach(function(row) {
        setRemarksReqdForCurrentRow(frm, 'evaluate_competency_items', row.name);
    });
}

function setRemarksReqdForCurrentRow(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    var reqdValue = row.evaluator_1 <= 1 ? 1 : 0;
    frappe.meta.get_docfield(cdt, 'eval_1_remarks', cdn).reqd = reqdValue;
}

var cal_final_score = (frm) => {
	let f_score = 0.0
	f_score = eval_1_score + eval_2_score + eval_3_score
	cur_frm.set_value("final_score", f_score);
	frm.refresh_fields() 
}

var cal_eval_total = (frm) => {
	let item = frm.doc.work_competency || [];
	let eval_1_score = 0.0, eval_2_score = 0.0, eval_3_score = 0.0, count = 0

	for (let i = 0; i < item.length; i++) {
		if (item[i].evaluator_1) {
			eval_1_score += parseFloat(item[i].evaluator_1);
		}
		if (item[i].evaluator_2) {
			eval_2_score += parseFloat(item[i].evaluator_2);
		}
		if (item[i].evaluator_3) {
			eval_3_score += parseFloat(item[i].evaluator_3);
		}
		count += 1
	}
	cur_frm.set_value("evaluator_1_score", eval_1_score/count);
	cur_frm.set_value("evaluator_2_score", eval_2_score/count);
	cur_frm.set_value("evaluator_3_score", eval_3_score/count);
}

var get_competency = (frm) => {
	if (frm.doc.employee_group) {
		return frappe.call({
			method: 'get_competency',
			doc: frm.doc,
			callback: ()=> {
				frm.refresh_field('competency');
				frm.refresh_fields()
			}
		})
	} else {
		frappe.msgprint('Your Employee Group is not defined under Employee')
	}
}

var get_evaluators = (frm) => {
	if (frm.doc.employee) {
		return frappe.call({
			method: 'get_evaluators',
			doc: frm.doc,
			callback: () => {
				frm.refresh_field('evaluator_1')
				frm.refresh_field('evaluator_2')
				frm.refresh_field('evaluator_3')
				frm.refresh_field('eval_1_name')
				frm.refresh_field('eval_2_name')
				frm.refresh_field('eval_3_name')
				frm.refresh_field('eval_1_user_id')
				frm.refresh_field('eval_2_user_id')
				frm.refresh_field('eval_3_user_id')
			}
		})
	}
}

var get_start_end_date = (frm) => {
	if (frm.doc.month) {
		return frappe.call({
			method: 'set_evaluation_period_dates',
			doc: frm.doc,
			callback: () => {
				frm.refresh_field('start_date')
				frm.refresh_field('end_date')
			}
		})
	}
}