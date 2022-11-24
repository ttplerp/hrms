# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.utils.nestedset import NestedSet, get_root_of

from erpnext.utilities.transaction_base import delete_events


class Dzongkhag(NestedSet):
	nsm_parent_field = "parent_dzongkhag"

	def autoname(self):
		self.name = self.dzongkhag_name

	def validate(self):
		if not self.parent_dzongkhag:
			root = get_root_of("Dzongkhag")
			if root:
				self.parent_dzongkhag = root

	def on_update(self):
		if not (frappe.local.flags.ignore_update_nsm or frappe.flags.in_setup_wizard):
			super(Dzongkhag, self).on_update()

	def on_trash(self):
		super(Dzongkhag, self).on_trash()
		delete_events(self.doctype, self.name)


def on_doctype_update():
	frappe.db.add_index("Dzongkhag", ["lft", "rgt"])


@frappe.whitelist()
def get_children(doctype, parent=None, company=None, is_root=False):
	fields = ["name as value", "is_group as expandable"]
	filters = {}

	if company == parent:
		filters["name"] = get_root_of("Dzongkhag")
	elif company:
		filters["parent_dzongkhag"] = parent
		filters["company"] = company
	else:
		filters["parent_dzongkhag"] = parent

	return frappe.get_all(doctype, fields=fields, filters=filters, order_by="name")


@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = frappe.form_dict
	args = make_tree_args(**args)

	if args.parent_dzongkhag == args.company:
		args.parent_dzongkhag = None

	frappe.get_doc(args).insert()
