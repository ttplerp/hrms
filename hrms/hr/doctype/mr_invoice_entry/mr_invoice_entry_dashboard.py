from frappe import _

def get_data():
	return {
        "fieldname": "mr_invoice_entry",
        "non_standard_fieldnames": {
			"Journal Entry": "referece_doctype",
		},
		"transactions": [
			{"label": _("Related Transaction"), "items": ["MR Employee Invoice","Journal Entry"]},
		],
	}