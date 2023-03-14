// Copyright (c) 2023, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dispatch CD', {
	onload: function (frm) {
		frm.set_value('date', frappe.datetime.get_today())	
	},
	refresh: function (frm) {
		frm.disable_save();
		let scan_barcode_field = frm.get_field('scan_barcode');
		if (scan_barcode_field && scan_barcode_field.get_value()) {
			frm.set_value('scan_barcode', '')	
		}
	},	
	// set default
	date: function (frm) {
		// should be less than =today
		if (frm.doc.date>frappe.datetime.get_today()) {
			frappe.throw(__('Date should be less than or equal to today.'))
		}
	},
	scan_barcode: function(frm) {

		if(frm.doc.scan_barcode) {
			frappe.call({
				method: "khozama.khozama.doctype.dispatch_cd.dispatch_cd.search_for_serial",
				args: {
					search_value: frm.doc.scan_barcode
				}
			}).then(r => {
				console.log('r',r)
				const data = r && r.message;
				if (!data || Object.keys(data).length === 0) {
					frappe.show_alert({
						message: __('Cannot find Item with this Barcode'),
						indicator: 'red'
					});
					frm.set_value('scan_barcode', '')		
					return;
				}else{
					//  do SE here
					let scan_barcode_field = frm.fields_dict["scan_barcode"];
					console.log('scan_barcode_field',scan_barcode_field)	
					let serial_no=r.message.serial_no
					let item_code=r.message.item_code
					let status=r.message.status
					if (serial_no==undefined) {
						frappe.show_alert({
							message: __('Cannot find Serial Item with this Barcode'),
							indicator: 'red'
						});
						frm.set_value('scan_barcode', '')		
						return;					
					}else if (frm.doc.target_warehouse==undefined || frm.doc.date==undefined) {
						frappe.show_alert({
							message: __('Warehouse or Date is missing. Please fill it first.'),
							indicator: 'red'
						});
						frm.set_value('scan_barcode', '')		
						return;

					}else if (status!='Inactive') {
						frappe.show_alert({
							message: __('Serial No status is {0}. and already exist',[status]),
							indicator: 'red'
						});
						frm.set_value('scan_barcode', '')		
						return;

					}
					else{
						frappe.call({
							'method': 'khozama.khozama.doctype.dispatch_cd.dispatch_cd.make_material_receipt',
							args: {
								serial_no: serial_no,
								item_code:item_code,
								target_warehouse:frm.doc.target_warehouse,
								posting_date:frm.doc.date
							},
							freeze: true,
							callback: function(r) {
								if (!r.exc) {
									
									if (r.message) {
										let url_list = '<a href="/app/stock-entry/'+ r.message + '" target="_blank">' + r.message + '</a><br>'
										frappe.msgprint({
											title: __('Material Receipt is created.'),
											indicator: 'green',
											message: __(url_list)
										})								
									}
									frm.set_value('scan_barcode', '')		
									return;									
									// frm.reload_doc();
								}
							}
						});						
					}

				}



			});
		}
		return false;
	},
});
