// Copyright (c) 2024, GreyCube Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Consumed Item Profit Loss Report"] = {
	"filters": [
		{
		 "fieldname": "customer",
		 "fieldtype": "Link",
		 "label": "Customer",
		 "options": "Customer",
		},
		{
		 "fieldname": "from_date",
		 "fieldtype": "Date",
		 "label": "From Date",
		},
		{
		 "fieldname": "to_date",
		 "fieldtype": "Date",
		 "label": "To Date",
		},
		{
		 "fieldname": "sales_order",
		 "fieldtype": "Link",
		 "label": "Document",
		 "options": "Sales Order",
		}
	   ],
};
