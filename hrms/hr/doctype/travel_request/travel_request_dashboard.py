from frappe import _

def get_data():
	return {
        "fieldname":"reference",
        "internal_links": {
			"Travel Request": ["expenses", "reference"],
		},
		"transactions": [
			{"label": _("Reference"), "items": ["Expense Claim","Employee Advance"]},
		],
	}
