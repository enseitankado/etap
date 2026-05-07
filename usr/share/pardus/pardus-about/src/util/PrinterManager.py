import cups


def get_printers():
    printers_list = []
    try:
        conn = cups.Connection()
        printers = conn.getPrinters()

        for p in printers:
            printer_obj = {
                "device_id": "",
                "name": printers[p]["printer-make-and-model"],
                "vendor": "",
                "driver": "",
                "available_drivers": [],
                "bus": "cups",
                "bus_address": "",
            }

            printers_list.append(printer_obj)
    except Exception as e:
        print("Exception on get_printers():", e)
        return []

    return printers_list
