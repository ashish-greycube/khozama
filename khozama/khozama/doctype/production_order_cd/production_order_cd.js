// Copyright (c) 2023, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Production Order CD', {
	onload:function(frm) {
		frm.set_query('item_code', 'consumable_items', () => {
			return {
				filters: {
					is_stock_item: 1
				}
			}
		})	
		frm.set_query('warehouse', 'consumable_items', () => {
			return {
				filters: {
					company: frm.doc.company
				}
			}
		})	
		frm.set_query('finished_item_code', 'consumable_items', () => {
			return {
				filters: {
					has_serial_no: 1,
					is_stock_item:1
				}
			}
		})					
	},
    refresh: function (frm) {
		if (frm.doc.docstatus == 0 && frm.is_new()==undefined && !frm.is_dirty()) {
			frm.add_custom_button(__("Material Issue/Transfer"),() => {
				if (!frm.is_dirty()) {
					frm.trigger('make_material_issue_dialog')
					
				} else {
					frappe.throw({
						title: __("Stop"),
						message: __('Please save the form to proceed...'),
						indicator: 'red'
					});											
				}
            }
            ,__("Create"));
            }
			else{
				frm.remove_custom_button('Create', 'Material Issue');
			}
    },
	make_material_issue_dialog: function (frm) {
		let consumable_items =$.map(frm.doc.consumable_items, function(d) { 
			if (d.planned_qty>0) {
				return {
					'idx':d.idx,
					'item_code':d.item_code,
					'item_name':d.item_name,
					'planned_qty':d.planned_qty,
					'remaining_qty':d.remaining_qty,
					'issued_qty':d.issued_qty,
					'to_issue_qty':0,
					'scrapped_qty':d.scrapped_qty,
					'to_scrap_qty':0,
					'item_hexcode':d.name,
					'warehouse':d.warehouse
				}; 			
			}
		});
		if (consumable_items.length>=1) {
			let title=__('Create Material Issue / Transfer');
			let fields= [
				{fieldtype:'Section Break', label: __('Consumable Items')},
				{
					fieldname: 'consumable_items_table',
					fieldtype: 'Table',
					label: __(''),
					// in_place_edit: true,
					cannot_add_rows: true,
					cannot_delete_rows: true,
					fields: [
						{
							fieldtype:'Data',
							fieldname:'item_code',
							label: __('Item'),
							in_list_view:1,
							hidden:1

						},
						{
							fieldtype:'Data',
							fieldname:'item_name',
							label: __('Name'),
							in_list_view:1,
							columns:2,
							read_only:1

						},
						{
							fieldtype:'Int',
							fieldname:'planned_qty',
							label: __('Planned qty'),
							in_list_view:1,
							columns:1,
							read_only:1							
						},		
						{
							fieldtype:'Int',
							fieldname:'remaining_qty',
							label: __('Remaining qty'),
							in_list_view:1,
							columns:1,
							read_only:1							
						},
						// {
						// 	fieldtype:'Int',
						// 	fieldname:'issued_qty',
						// 	label: __('Issued qty'),
						// 	in_list_view:1,
						// 	columns:1,
						// 	read_only:1							
						// },
						{
							fieldtype:'Int',
							fieldname:'to_issue_qty',
							label: __('To Issue qty'),
							in_list_view:1,
							columns:2,
						},	
						// {
						// 	fieldtype:'Int',
						// 	fieldname:'scrapped_qty',
						// 	label: __('Scrapped qty'),
						// 	in_list_view:1,
						// 	read_only:1,
						// 	columns:1,							

						// },
						{
							fieldtype:'Int',
							fieldname:'to_scrap_qty',
							label: __('To Scrap qty'),
							in_list_view:1,
							columns:2
						},																																	
					],
					data: consumable_items,
					get_data: () => {
						return consumable_items
					},

				},
			]
			let d=new frappe.ui.Dialog({
				title:title,
				fields: fields,
				primary_action_label: 'Issue',
				primary_action: function() {
					var data = d.get_values();
					let selected_consumable_items=data.consumable_items_table
					//  validations:
					let found_qty_to_scrap_or_issue=false
					for (let index = 0; index < selected_consumable_items.length; index++) {

						let row=selected_consumable_items[index]
				
						if (row.to_scrap_qty >0 ||  row.to_issue_qty>0){
							found_qty_to_scrap_or_issue=true

						}
						
						
					}
					if (found_qty_to_scrap_or_issue==false) {
						d.hide()
						frappe.msgprint({
							title: __("No Action "),
							message: __('No quanitity inputed for issue or scrap.'),
							indicator: 'yellow'
						});						
					}else{
						console.log(selected_consumable_items,'consumable_items',consumable_items)
						console.log('dialog.fields_dict.sub_con_rm_items.grid',d.fields_dict.consumable_items_table.grid)
						
						frappe.call({
							method:"khozama.khozama.doctype.production_order_cd.production_order_cd.make_stock_entry_for_consumable_items",
							args: {
								'consumable_items':selected_consumable_items,
								'production_order' :cur_frm.doc.name
							},
							callback: function(r) {
								d.hide();
								console.log(r,'r')
								// if (r.message) {
								// 	let url_list = '<a href="/app/stock-entry/'+ r.message + '" target="_blank">' + r.message + '</a><br>'
								// 	frappe.msgprint({
								// 		title: __('Material Issue is created.'),
								// 		indicator: 'green',
								// 		message: __(url_list)
								// 	})								
								// }
								// var doclist = frappe.model.sync(r.message);
								// frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
							}
						});							
					}
					
				}				
		})
		d.show();
		d.get_close_btn().on('click', () => {
			d.hide();
		});		
	}
}
});
frappe.ui.form.on("Production Order Consumable Item CT", {
	item_code: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn]
		if (row.item_code) {
			frappe.call('khozama.khozama.doctype.production_order_cd.production_order_cd.get_item_default_warehouse', {
				item_code: row.item_code,
				company:frm.doc.company

			}).then(r => {
				console.log(r.message)
				frappe.model.set_value(cdt, cdn, "warehouse", r.message);
			})			
		}
	},
	issued_qty: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn]
		calculate_to_consume_qty(cdt, cdn,row)
	},
    consumption_qty: function (frm, cdt, cdn) {
        debugger
        let row = locals[cdt][cdn]
		if (row.consumption_qty< row.planned_qty) {
			frappe.throw({
				title: __("Cosumption qty is less"),
				message: __('Item Code: {0} has consumption qty {1}, which is less than planned qty {2}.', [row.item_code, row.consumption_qty,row.planned_qty]),
				indicator: 'red'
			});			
		}
		if (row.consumption_qty< row.issued_qty) {
			frappe.throw({
				title: __("Cosumption qty is less"),
				message: __('Item Code: {0} has consumption qty {1}, which is less than issued qty {2}.', [row.item_code, row.consumption_qty,row.issued_qty]),
				indicator: 'red'
			});			
		}	
		calculate_to_consume_qty(cdt, cdn,row)	
    },
})

function calculate_to_consume_qty(cdt, cdn,row) {
	debugger
	let to_consume_qty=row.consumption_qty-row.issued_qty
	frappe.model.set_value(cdt, cdn, "to_consume_qty", to_consume_qty);
	

	
}

function make_material_issue_stock_entry(consumable_items,frm) {
	console.log(consumable_items,'consumable_items')
	frappe.call({
		method:"khozama.khozama.doctype.production_order_cd.production_order_cd.make_material_issue_stock_entry",
		args: {
			consumable_items: consumable_items,
			frm: frm
		}
		,
		callback: function(r) {
			console.log(r,'r')
			var doclist = frappe.model.sync(r.message);
			frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	});	
}