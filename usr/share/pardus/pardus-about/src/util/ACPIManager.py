def is_acpi_supported():
    """Requires root permission. Use only in Actions.py with pkexec."""

    with open("/sys/firmware/acpi/tables/DSDT", "rb") as f:
        return "linux" in str(f.read()).lower()
