import os
import time
import logging
import urllib.parse
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import config

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scraper.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("DragonCapitalScraper")

class DragonCapitalScraper:
    def __init__(self):
        self.base_url = config.BASE_URL
        self.download_dir = config.BASE_DOWNLOAD_DIR
        self.driver = None
        self.wait = None

    def init_driver(self):
        """Initialize Selenium Chrome Driver with Headless Mode and custom options."""
        logger.info("Initializing Selenium Chrome WebDriver...")
        chrome_options = Options()
        if config.HEADLESS:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Set automatic download preferences
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, config.EXPLICIT_WAIT)
        logger.info("WebDriver successfully initialized.")

    def open_page(self):
        """Navigate to the Dragon Capital report page."""
        logger.info(f"Opening target page: {self.base_url}")
        self.driver.get(self.base_url)
        time.sleep(5)  # Allow LWC components to load completely

    def click_element_safely(self, element):
        """Click an element using JavaScript to bypass overlap issues."""
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.3)
        self.driver.execute_script("arguments[0].click();", element)

    def select_dropdown_option(self, input_xpath, option_text):
        """
        Click on custom dropdown input and select an option matching option_text.
        """
        try:
            logger.info(f"Selecting dropdown option: '{option_text}'")
            input_elem = self.wait.until(EC.element_to_be_clickable((By.XPATH, input_xpath)))
            self.click_element_safely(input_elem)
            time.sleep(1.5)

            # Find matching option LI
            options_xpath = "//ul[contains(@class, 'options')]/li[contains(@class, 'option')]"
            options = self.driver.find_elements(By.XPATH, options_xpath)
            
            target_option = None
            for opt in options:
                txt = opt.text.strip()
                if txt.lower() == option_text.lower() or option_text.lower() in txt.lower():
                    target_option = opt
                    break

            if target_option:
                self.click_element_safely(target_option)
                logger.info(f"Successfully selected: '{option_text}'")
                time.sleep(3)  # Wait for dynamic table update
                return True
            else:
                logger.warning(f"Option '{option_text}' not found in dropdown list.")
                return False
        except Exception as e:
            logger.error(f"Error selecting dropdown option '{option_text}': {e}")
            return False

    def get_available_years():
        """Retrieve all available years from the Year dropdown."""
        pass  # Implemented in main loop below

    def expand_all_accordions(self):
        """Expand all (+) accordion items to reveal hidden attachment download links."""
        try:
            toggle_icons = self.driver.find_elements(By.XPATH, config.SELECTORS["toggle_icons"])
            logger.info(f"Found {len(toggle_icons)} accordion items to expand.")
            for idx, icon in enumerate(toggle_icons):
                try:
                    self.click_element_safely(icon)
                    time.sleep(0.3)
                except Exception as ex:
                    logger.debug(f"Could not click toggle icon {idx}: {ex}")
            time.sleep(1.5)
        except Exception as e:
            logger.warning(f"Error expanding accordions: {e}")

    def download_excel_file(self, file_url, fund_name, year, preferred_name=None):
        """
        Download file via requests into downloads/<FUND>/<YEAR>/ directory.
        Checks for existing file to avoid duplicate downloads.
        """
        try:
            target_dir = os.path.join(self.download_dir, fund_name, str(year))
            os.makedirs(target_dir, exist_ok=True)

            # Determine filename
            parsed_url = urllib.parse.urlparse(file_url)
            url_filename = os.path.basename(parsed_url.path)
            
            if preferred_name:
                ext = os.path.splitext(url_filename)[1] or ".xlsx"
                # Clean invalid filename characters
                safe_name = "".join(c for c in preferred_name if c.isalnum() or c in (" ", "_", "-", ".")).strip()
                if not safe_name.endswith(ext):
                    filename = f"{safe_name}{ext}"
                else:
                    filename = safe_name
            else:
                filename = url_filename

            filepath = os.path.join(target_dir, filename)

            # Deduplication check
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                logger.info(f"File already exists (skipping): {filepath}")
                return True

            logger.info(f"Downloading [{fund_name} - {year}]: {filename}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            res = requests.get(file_url, headers=headers, timeout=30)
            res.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(res.content)

            logger.info(f"Saved: {filepath} ({len(res.content)} bytes)")
            return True

        except Exception as e:
            logger.error(f"Failed to download {file_url}: {e}")
            return False

    def scrape_fund_and_years(self, fund_name):
        """Scrape all Excel files for a specific fund across all available years."""
        logger.info(f"\n=================== START SCRAPING FUND: {fund_name} ===================")
        
        # 1. Select Fund
        if not self.select_dropdown_option(config.SELECTORS["fund_input"], fund_name):
            logger.error(f"Skipping fund {fund_name} due to dropdown selection failure.")
            return

        # 2. Select Document Type if specified
        if config.TARGET_DOC_TYPE:
            self.select_dropdown_option(config.SELECTORS["doc_type_input"], config.TARGET_DOC_TYPE)

        # 3. Get list of available years
        try:
            year_input = self.wait.until(EC.element_to_be_clickable((By.XPATH, config.SELECTORS["year_input"])))
            self.click_element_safely(year_input)
            time.sleep(1.5)

            year_options = self.driver.find_elements(By.XPATH, config.SELECTORS["options_list"])
            available_years = [opt.text.strip() for opt in year_options if opt.text.strip().isdigit()]
            logger.info(f"Available years for {fund_name}: {available_years}")

            # Close year dropdown by clicking outside or clicking year input again
            self.click_element_safely(year_input)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Could not fetch year options for {fund_name}: {e}")
            available_years = ["2026", "2025", "2024", "2023", "2022", "2021"]

        # 4. Iterate over each year
        for year in available_years:
            logger.info(f"\n--- Processing Fund {fund_name} | Year {year} ---")
            
            # Select Year option
            if not self.select_dropdown_option(config.SELECTORS["year_input"], year):
                logger.warning(f"Could not select year {year} for fund {fund_name}. Skipping year.")
                continue

            # Expand accordions to reveal download links
            self.expand_all_accordions()

            # Extract download links
            links = self.driver.find_elements(By.XPATH, config.SELECTORS["download_links"])
            logger.info(f"Found {len(links)} total download links for year {year}")

            excel_count = 0
            for link in links:
                try:
                    href = link.get_attribute("href")
                    title = link.get_attribute("download") or link.text.strip()
                    
                    if not href:
                        continue

                    # Filter for Excel files (.xlsx, .xls, .csv)
                    is_excel = any(href.lower().endswith(ext) or ext in href.lower() for ext in config.EXCEL_EXTENSIONS)
                    
                    if is_excel:
                        excel_count += 1
                        self.download_excel_file(file_url=href, fund_name=fund_name, year=year, preferred_name=title)
                except Exception as ex:
                    logger.warning(f"Error processing link element: {ex}")

            logger.info(f"Completed Year {year} for {fund_name}. Downloaded/Verified {excel_count} Excel files.")

    def run(self):
        """Main execution flow."""
        start_time = time.time()
        try:
            self.init_driver()
            self.open_page()

            for fund in config.TARGET_FUNDS:
                self.scrape_fund_and_years(fund)

            elapsed = round(time.time() - start_time, 2)
            logger.info(f"\n Scraping completed successfully in {elapsed} seconds!")
            logger.info(f"All files saved under: {self.download_dir}")

        except Exception as e:
            logger.error(f"Critical error during scraping execution: {e}", exc_info=True)
        finally:
            if self.driver:
                logger.info("Closing Chrome WebDriver.")
                self.driver.quit()

if __name__ == "__main__":
    scraper = DragonCapitalScraper()
    scraper.run()
