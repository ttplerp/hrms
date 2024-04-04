// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Employee Advance'] = {
	get_indicator: function(doc) {
		var status_color = {
			'Draft': 'red',
			'Paid': 'blue',
			'Unpaid': 'orange',
			'Cancelled': 'red'

		};
		return [__(doc.status), status_color[doc.status], 'status,=,'+doc.status];
	}
};
