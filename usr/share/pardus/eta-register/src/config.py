# -*- coding: utf-8 -*-

"""
Configuration settings for the ETA Register application.
"""

import os

user_home = os.path.expanduser('~')
user_cache_dir = os.path.join(user_home, ".cache/eta-register")

# For development, use the local backend server.
# For production, this will be "http://api-etap.eba.gov.tr:1000/api"
# for testing, this will be "http://161.9.194.158:3000/api"
BACKEND_URL = "http://api-etap.eba.gov.tr:1000/api"


# Secret header for authenticating with the backend API.
SECURE_HEADER = {"etap-app-code": "eta_register!"}
PACKAGE_TO_INSTALL = "ahenk"  # Use "ahenk" for production
SERVICE_TO_ENABLE = "ahenk.service"
VENDOR_LIST_URL = "https://etap.org.tr/devices.json"
VENDOR_CONTACT_EMAIL = "eta@pardus.org.tr"

# --- Application Constants ---
APPNAME = "eta-register"
APPNAME_CODE = "eta-register"
TRANSLATIONS_PATH = "/usr/share/locale"
LOG_FILE = os.path.join(user_cache_dir, "eta-register.log")
REQUIRED_USER = "etapadmin"
