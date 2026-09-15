import os

# Base URL of Dragon Capital Reports Page
BASE_URL = "https://www.dragoncapital.com.vn/individual/vi/report"

# Target Funds to scrape
TARGET_FUNDS = ["DCDS", "DCDE","DCBF","DCIP","Diamond"]

# Target Document Type (Set to None or 'Loại tài liệu: Tất cả' to get all, or specify category)
# Options: 'Loại tài liệu: Tất cả', 'Công bố thông tin quỹ', 'Tài liệu quỹ và biểu mẫu'
TARGET_DOC_TYPE = "Loại tài liệu: Tất cả"

# Base Download Directory
BASE_DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")

# Selenium Browser Settings
HEADLESS = True
IMPLICIT_WAIT = 10
EXPLICIT_WAIT = 15

# Supported Excel Extensions to filter
EXCEL_EXTENSIONS = [".xlsx", ".xls", ".csv"]

# DOM Selectors (Verified from Dragon Capital LWC dynamic page)
SELECTORS = {
    "fund_input": "//input[@name='fundName']",
    "doc_type_input": "//input[@name='documentType']",
    "year_input": "//input[@name='year']",
    "options_list": "//ul[contains(@class, 'options')]/li[contains(@class, 'option')]",
    "toggle_icons": "//div[contains(@class, 'toggle-icon')]",
    "download_links": "//a[contains(@class, 'download-link') or contains(@href, 'dragoncapitalprod.blob.core.windows.net')]"
}
