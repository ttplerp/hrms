from frappe import _

def get_data():
	return {
        "fieldname":"reference_name",
        "internal_links": {
			"MPI Transaction": ["accounts", "reference_name"],
		},
		"transactions": [
			{"label": _("Reference"), "items": ["Journal Entry"]},
		],
	}