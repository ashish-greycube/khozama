frappe.ui.form.on("Sales Order", {
    refresh: function (frm) {
        debugger
		if (frm.doc.docstatus == 1 && frm.is_new()==undefined && frm.doc.items && frm.doc.items.length==1) {
			frm.add_custom_button(__("Production Order"),() => {
                make_production_order(frm)
            }
            ,__("Create")
            );
            }
    }
})

frappe.ui.form.on("Sales Order Item", {
    height_cf: function (frm, cdt, cdn) {
        debugger
        let row = locals[cdt][cdn]
        let area = calculate_area(row.height_cf,row.width_cf)
        frappe.model.set_value(cdt, cdn, "area_cf", area);
    },
    width_cf: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn]
        let area = calculate_area(row.height_cf,row.width_cf)
        frappe.model.set_value(cdt, cdn, "area_cf", area);
    },
    area_cf: function (frm, cdt, cdn) {
        let area_for_calculation_cf
        let row = locals[cdt][cdn]
        if (row.area_cf < 0.5) {
            area_for_calculation_cf = 0.5
        } else {
            area_for_calculation_cf = row.area_cf
        }
        frappe.model.set_value(cdt, cdn, "area_for_calculation_cf", area_for_calculation_cf);
    },
    no_of_pcs_cf: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn]
        let qty=calculate_total_area(row.no_of_pcs_cf, row.area_for_calculation_cf)
        frappe.model.set_value(cdt, cdn, "qty", qty);
    },
    area_for_calculation_cf: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn]
        let qty=calculate_total_area(row.no_of_pcs_cf, row.area_for_calculation_cf)
        frappe.model.set_value(cdt, cdn, "qty", qty);
    }    
});

function calculate_area(height, width) {
    let area = flt((height * width) / 1000000)
    return area
}

function calculate_total_area(no_of_pcs_cf, area_for_calculation_cf) {
    let qty = flt(no_of_pcs_cf * area_for_calculation_cf)
    return qty
}

function make_production_order(frm) {
	frappe.model.open_mapped_doc({
		method: "khozama.khozama.doctype.production_order_cd.production_order_cd.make_production_order",
		frm: frm
	})    
}