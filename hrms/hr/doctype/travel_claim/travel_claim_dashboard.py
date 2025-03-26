from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
	'fieldname': 'name',
		'non_standard_fieldnames': {
			'Travel Authorization': 'travel_claim',
			'Journal Entry': 'reference_name',
		},
		'transactions': [
			{"label": _("Travel Authorization"), "items": ["Travel Authorization"]},
			{"label": _("Payments"), "items": ["Journal Entry"]},
		]
	}
