// Filters for Print Waste. The reasons are the job card's own options (fuse_print/waste.py REASONS).
frappe.query_reports["Print Waste"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -2),
		},
		{
			fieldname: "to_date",
			label: __("To"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "workstation",
			label: __("Workstation"),
			fieldtype: "Link",
			options: "Workstation",
		},
		{
			fieldname: "reason",
			label: __("Reason"),
			fieldtype: "Select",
			options: [
				"",
				"Setup and colour match",
				"Misprint",
				"Media fault",
				"Lamination fault",
				"Cut out of register",
				"Weeding damage",
				"End of roll",
				"Other",
			],
		},
	],

	// A step that spoiled something stands out without reading the numbers.
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.waste > 0 && ["waste", "waste_pct", "cost"].includes(column.fieldname)) {
			value = `<span style="color: var(--red-600, #b02a37)">${value}</span>`;
		}
		return value;
	},
};
