frappe.ui.form.on('Kitchen Printer', {
    refresh(frm) {

        // Test Connection
        frm.add_custom_button('Test Connection', () => {
            frappe.call({
                method: "cook_desk.api.printer.test_connection",
                args: {
                    ip: frm.doc.ip_address,
                    port: frm.doc.port || 9100
                },
                callback: function(r) {
                    frappe.msgprint(r.message);
                }
            });
        });

        // Test Print
        frm.add_custom_button('Test Print', () => {
            frappe.call({
                method: "cook_desk.api.printer.test_print",
                args: {
                    ip: frm.doc.ip_address,
                    port: frm.doc.port || 9100
                },
                callback: function(r) {
                    frappe.msgprint(r.message);
                }
            });
        });

    }
});
