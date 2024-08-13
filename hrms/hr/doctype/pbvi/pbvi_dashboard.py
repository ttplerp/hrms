from frappe import _

def get_data():
	return {
        "fieldname":"reference_name",
        "internal_links": {
			"PBVA": ["accounts", "reference_name"],
		},
		"transactions": [
			{"label": _("Reference"), "items": ["Journal Entry"]},
		],
	}