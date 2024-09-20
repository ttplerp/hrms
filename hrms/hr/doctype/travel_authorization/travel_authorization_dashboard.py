from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
	'fieldname': 'name',
		'non_standard_fieldnames': {
			'Travel Claim': 'ta',
		},
		'transactions': [
			{
				'label': _('Travel Claim'),
				'items': ['Travel Claim']
			}
		]
	}
