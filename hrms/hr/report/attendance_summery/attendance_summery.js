frappe.query_reports["Attendance Summery"] = {
    "filters": [
        {
            fieldname: "fiscal_year",
            label: __("Fiscal Year"),
            fieldtype: "Select",
            reqd: 1
        },
        {
            fieldname: "month",
            label: __("Month"),
            fieldtype: "Select",
            reqd: 1
        }
    ],

    onload: function(report) {
        const monthNames = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ];

        // Fetch all fiscal years
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Fiscal Year",
                fields: ["year", "year_start_date", "year_end_date"],
                order_by: "year_start_date desc"
            },
            callback: function(r) {
                if (r.message) {
                    const fy_filter = report.get_filter("fiscal_year");
                    const today = frappe.datetime.get_today();
                    let default_year = r.message[0].year;

                    // Set fiscal year dropdown
                    fy_filter.df.options = r.message.map(fy => fy.year).join("\n");

                    // Select current fiscal year if today falls in it
                    r.message.forEach(fy => {
                        if (fy.year_start_date <= today && fy.year_end_date >= today) {
                            default_year = fy.year;
                        }
                    });

                    fy_filter.set_input(default_year);
                    fy_filter.refresh();

                    // Populate months based on selected fiscal year
                    update_month_options(default_year, report, r.message);
                }
            }
        });

        // Handle fiscal year change
        report.get_filter("fiscal_year").on_change = function() {
            const selected_year = report.get_values().fiscal_year;
            update_month_options(selected_year, report);
        };

        // Function to populate month options
        function update_month_options(fiscal_year, report, fy_list=null) {
            const monthNames = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ];

            const month_filter = report.get_filter("month");
            let fy = null;

            if (fy_list) {
                fy = fy_list.find(f => f.year === fiscal_year);
            } else {
                // fetch fiscal year data if fy_list not provided
                frappe.call({
                    method: "frappe.client.get_value",
                    args: {
                        doctype: "Fiscal Year",
                        fieldname: ["year_start_date", "year_end_date"],
                        filters: { year: fiscal_year }
                    },
                    async: false,
                    callback: function(r) {
                        fy = r.message;
                    }
                });
            }

            if (fy) {
                const today = new Date();
                const fy_start = new Date(fy.year_start_date);
                const fy_end = new Date(fy.year_end_date);

                let months = monthNames.slice();

                // If current fiscal year → only past/current months
                if (fy_start <= today && fy_end >= today) {
                    months = monthNames.slice(0, today.getMonth() + 1);
                }

                month_filter.df.options = months.join("\n");
                month_filter.set_input(months[months.length - 1]); // last month as default
                month_filter.refresh();

                // Run report automatically after filters are ready
                report.refresh();
            }
        }
    }
};
