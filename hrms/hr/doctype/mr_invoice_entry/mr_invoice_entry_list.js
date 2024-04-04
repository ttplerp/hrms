// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
frappe.listview_settings['MR Invoice Entry'] = {
	add_fields: ["status"],
	has_indicator_for_draft: 1,
	get_indicator: function(doc) {
		const status_colors = {
			"Unpaid": "orange",
			"Paid": "green",
			"Cancelled": "red",
			"Draft": "red",
			"Submitted": "blue",
		};

		if (status_colors[doc.status]) {
			return [
				__(doc.status),
				status_colors[doc.status],
				"status,=," + doc.status,
			];
		}
	}
};

