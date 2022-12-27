// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["PF Report"] = {
	"filters": [
		{
			"fieldname":"month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": "Jan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
			"default": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
				"Dec"][frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()],
		},
		{
			"fieldname":"fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": sys_defaults.fiscal_year,
		},
		{
			"fieldname":"employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
                        "fieldname":"tier",
                        "label": __("Tier"),
                        "fieldtype": "Select",
                        "options":[" ", 1, 2],
                },
		{
			"fieldname":"cost_center",
			"label": __("Parent Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center"
		}
	
	],

/*	onload: function(report) {
		select = $('div[data-fieldname="test"]').children()
		frappe.call({
			method: "erpnext.hr.doctype.employee.employee.get_list",
			callback: function(r) {
				$.each(r.message, function(i, j) {
					select.append($('<option>', {value: i, text: j}))
				})
			}
		})
	} */
}
