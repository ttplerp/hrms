// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Upload Overtime Entries Tool', {
    onload: function() {
	},

	refresh: function(frm) {
		// frm.disable_save();
		// frm.events.show_upload();
	},
    upload_data:function(frm){
        frappe.call({
            method:"upload_data",
            doc:frm.doc,
            callback:function(r){
                
            },
            freeze: true,
			freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Uploading Data.....</span>'
        })
    },
	get_template:function(frm) {
		if(!frm.doc.fiscal_year || !frm.doc.month || !frm.doc.branch || !frm.doc.file_type) {
			msgprint(__("Fiscal Year, Month, Branch and File Type are mandatory"));
			return;
		}
        open_url_post(
            '/api/method/hrms.hr.doctype.upload_overtime_entries_tool.upload_overtime_entries_tool.download_template',
            {
                file_type: frm.doc.file_type,
                branch : frm.doc.branch,
                month: frm.doc.month,
                fiscal_year: frm.doc.fiscal_year
            }
        )
	},

	show_upload: function(frm) {
		var me = frm;
		var $wrapper = $(cur_frm.fields_dict.upload_html.wrapper).empty();

		// upload
		frappe.call({
			parent: $wrapper,
			// args: {
			method: 'hrms.hr.doctype.upload_overtime_entries.upload_overtime_entries.upload',
			// },
			sample_url: "e.g. http://example.com/somefile.csv",
			callback: function(attachment, r) {
				var $log_wrapper = $(cur_frm.fields_dict.import_log.wrapper).empty();

				if(!r.messages) r.messages = [];
				// replace links if error has occured
				if(r.exc || r.error) {
					r.messages = $.map(r.message.messages, function(v) {
						var msg = v.replace("Inserted", "Valid")
							.replace("Updated", "Valid").split("<");
						if (msg.length > 1) {
							v = msg[0] + (msg[1].split(">").slice(-1)[0]);
						} else {
							v = msg[0];
						}
						return v;
					});

					r.messages = ["<h4 style='color:red'>"+__("Import Failed!")+"</h4>"]
						.concat(r.messages)
				} else {
					r.messages = ["<h4 style='color:green'>"+__("Import Successful!")+"</h4>"].
						concat(r.message.messages)
				}

				$.each(r.messages, function(i, v) {
					var $p = $('<p>').html(v).appendTo($log_wrapper);
					if(v.substr(0,5)=='Error') {
						$p.css('color', 'red');
					} else if(v.substr(0,8)=='Inserted') {
						$p.css('color', 'green');
					} else if(v.substr(0,7)=='Updated') {
						$p.css('color', 'green');
					} else if(v.substr(0,5)=='Valid') {
						$p.css('color', '#777');
					}
				});
			}
		});

		// rename button
		$wrapper.find('form input[type="submit"]')
			.attr('value', 'Upload and Import')
	}
});
