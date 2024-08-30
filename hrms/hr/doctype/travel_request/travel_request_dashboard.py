from frappe import _

def get_data():
	return {
        "fieldname":"reference",
		'non_standard_fieldnames': {
			'Training Event': 'travel_request_id',
		},
        "internal_links": {
			"Travel Request": ["expenses", "reference"],
		},
		"transactions": [
			{"label": _("Reference"), "items": ["Expense Claim","Employee Advance","Training Event"]},
		],
	}
