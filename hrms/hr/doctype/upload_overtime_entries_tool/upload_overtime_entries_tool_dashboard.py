from frappe import _

def get_data():
	return {
        "fieldname": "reference",
		"transactions": [
			{"label": _("Related Transaction"), "items": ["Master Roll Overtime Entries"]},
		],
	}