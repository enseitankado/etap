#!/usr/bin/python3

import sys
import os
import subprocess

from util import ACPIManager
from util import DualBootManager
from util import SystemReportManager


def run(cmd, capture_output=False):
    return subprocess.run(
        ["pkexec", os.path.abspath(__file__), cmd],
        capture_output=capture_output,
    )


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        cmd = sys.argv[1]

        if cmd == "acpi":
            if ACPIManager.is_acpi_supported():
                sys.exit(0)
            else:
                sys.exit(1)
        elif cmd == "report":
            SystemReportManager.generate_report()
        elif cmd == "dualboot":
            print(DualBootManager.get_dualboot_oses())
