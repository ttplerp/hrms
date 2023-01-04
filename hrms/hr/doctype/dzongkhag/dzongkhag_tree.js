frappe.treeview_settings["Dzongkhag"] = {
	ignore_fields:["parent_dzongkhag"],
	get_tree_nodes: 'hrms.hr.doctype.dzongkhag.dzongkhag.get_children',
	add_tree_node: 'hrms.hr.doctype.dzongkhag.dzongkhag.add_node',
	filters: [
		{
			fieldname: "company",
			fieldtype:"Link",
			options: "Company",
			label: __("Company"),
		},
	],
	breadcrumb: "HR",
	root_label: "All Dzongkhag",
	get_tree_root: true,
	menu_items: [
		{
			label: __("New Dzongkhag"),
			action: function() {
				frappe.new_doc("Dzongkhag", true);
			},
			condition: 'frappe.boot.user.can_create.indexOf("Dzongkhag") !== -1'
		}
	],
	onload: function(treeview) {
		treeview.make_tree();
	}
};