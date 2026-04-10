import socket
import frappe


# ===============================
# LOW LEVEL SEND (CORE)
# ===============================
def send_to_printer(ip, port, content):
    try:
        s = socket.socket()
        s.settimeout(5)
        s.connect((ip, int(port)))

        # ------------------------
        # SEND TEXT
        # ------------------------
        s.sendall(content.encode('utf-8'))

        # ------------------------
        # FEED PAPER (VERY IMPORTANT)
        # ------------------------
        s.sendall(b'\n\n\n\n\n\n')

        # ------------------------
        # UNIVERSAL CUT COMMANDS 🔥
        # (TRY ALL — DIFFERENT PRINTERS)
        # ------------------------

        # Epson Full Cut
        s.sendall(b'\x1d\x56\x00')


        # ------------------------
        s.close()

    except Exception as e:
        frappe.log_error(f"{ip}:{port} -> {str(e)}", "Printer Error")


# ===============================
# BACKGROUND QUEUE PRINT
# ===============================
def enqueue_print(ip, port, content):
    frappe.enqueue(
        "cook_desk.api.printer.send_to_printer",
        queue="short",
        timeout=15,
        ip=ip,
        port=port,
        content=content
    )


# ===============================
# TEST CONNECTION
# ===============================
@frappe.whitelist()
def test_connection(ip, port):
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((ip, int(port)))
        s.close()

        return "✅ Printer Connected Successfully"

    except Exception as e:
        return f"❌ Connection Failed: {str(e)}"


# ===============================
# TEST PRINT
# ===============================
@frappe.whitelist()
def test_print(ip, port):
    try:
        content = "\n\n*** TEST PRINT ***\nCook Desk Working\n\n\n"
        enqueue_print(ip, port, content)

        return "🖨️ Test Print Sent"

    except Exception as e:
        return f"❌ Print Failed: {str(e)}"
