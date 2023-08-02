// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Performance Evaluation', {
	onload_post_render: function (frm) {
		$(".grid-add-row").addClass('hidden');
	},

	// onload: function (frm) {
	// },

	// refresh: function(frm) {
	// },

	month: (frm) => {
		get_start_end_date(frm);
	},
});

frappe.ui.form.on('Evaluate Competency Item', {
	evaluator: function(frm, cdt, cdn) {
		cal_eval_total(frm)
	},
});


var cal_eval_total = (frm) => {
	let item = frm.doc.work_competency || [];
	let evaluator_score = 0.0, count = 0

	for (let i = 0; i < item.length; i++) {
		if (item[i].evaluator) {
			evaluator_score += parseFloat(item[i].evaluator);
		}
		count += 1
	}
	console.log(evaluator_score);
	cur_frm.set_value("evaluator_score", evaluator_score/count);
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