import json
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time


class PakWheelsNavigator:
    """Handles browser initialization with UA rotation & basic navigation."""

    DEFAULT_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/16.4 Safari/605.1.15",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:116.0) Gecko/20100101 Firefox/116.0",
    ]

    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        self.driver = None
        self.wait = None

    def _load_config(self, config_path):
        try:
            with open(config_path, 'r') as f:
                cfg = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            cfg = {
                "search_url": "https://www.pakwheels.com/used-cars/search/-/",
                "comparison_url": "https://www.pakwheels.com/new-cars/compare/",
                "webdriver_wait_timeout": 20,
                "browser": "chrome",
                "headless": False,
                "user_agents": []
            }
        return cfg
    
    def _close_google_signin_popup(self, timeout: int = 5) -> bool:
        """
        Detects the Google sign‑in iframe, switches into it, clicks its close button,
        then returns to the main page. Returns True if the popup was found & closed.
        """
        try:
            iframe = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//iframe[contains(@src,'accounts.google.com/gsi/iframe/select')]"
                ))
            )
            print("  → Found Google sign‑in iframe")

            self.driver.switch_to.frame(iframe)

            close_btn = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.ID, "close"))
            )
            print("  → Found iframe close button, clicking it")
            close_btn.click()

            self.driver.switch_to.default_content()
            print("  → Switched back to main document")

            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located((
                    By.XPATH,
                    "//iframe[contains(@src,'accounts.google.com/gsi/iframe/select')]"
                ))
            )
            print("  → Google‑Sign‑In popup closed")
            return True

        except TimeoutException:
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            print("  → No Google‑Sign‑In popup detected")
            return False
        except Exception as e:
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            print(f"  ✖ Error closing Google‑Sign‑In popup: {e}")
            return False

    def initialize_driver(self):
        """Initializes Selenium WebDriver with UA rotation & stealth settings."""
        browser_type = self.config.get("browser", "chrome").lower()
        is_headless = self.config.get("headless", False)
        timeout = self.config.get("webdriver_wait_timeout", 20)
        page_load = self.config.get("page_load_timeout", 90)

        ua_list = self.config.get("user_agents") or self.DEFAULT_UAS
        user_agent = random.choice(ua_list)

        # Common options
        if browser_type == "chrome":
            options = webdriver.ChromeOptions()
            if is_headless:
                options.add_argument("--headless")
                options.add_argument("--window-size=1920,1080")
            # Stealth flags
            options.add_argument(f"--user-agent={user_agent}")
            options.add_argument(
                "--disable-blink-features=AutomationControlled")
            options.add_argument("--lang=en-US,en;q=0.9")
            options.add_experimental_option(
                "excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            self.driver = webdriver.Chrome(options=options)
        elif browser_type == "firefox":
            options = webdriver.FirefoxOptions()
            if is_headless:
                options.add_argument("--headless")
            options.set_preference("general.useragent.override", user_agent)
            options.set_preference("intl.accept_languages", "en-US,en;q=0.9")
            self.driver = webdriver.Firefox(options=options)
        else:
            raise ValueError(f"Unsupported browser type: {browser_type}")

        try:
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """}
            )
        except Exception:
            pass

        self.driver.maximize_window()
        try:
            self.driver.set_page_load_timeout(page_load)
        except Exception as e:
            print(f"Warning: Could not set page load timeout: {e}")

        self.wait = WebDriverWait(self.driver, timeout)
        print(f"{browser_type.capitalize()} driver ready with UA:\n  {user_agent}")
        return self.driver, self.wait

    def go_to_search_page(self):
        """Navigates to the base search URL specified in the config."""
        if not self.driver:
            raise WebDriverException(
                "WebDriver not initialized. Call initialize_driver() first.")
        search_url = self.config.get("search_url")
        if not search_url:
            raise ValueError("Base URL not found in configuration.")
        try:
            self.driver.get(search_url)
            print(f"Navigated to search page: {search_url}")
            self._close_google_signin_popup
        except Exception as e:
            print(f"Error navigating to {search_url}: {e}")
            self.close_driver()
            raise

    def open_listing_page_new_tab(self, listing_url: str) -> str | None:
        """Opens a new tab with the given listing URL, switches to it, and returns the new tab's handle."""
        if not self.driver:
            raise WebDriverException("WebDriver not initialized.")

        original_window = self.driver.current_window_handle
        try:
            self.driver.execute_script(
                f"window.open('{listing_url}', '_blank');")
            print(f"Opened new tab with URL: {listing_url}")

            self.wait.until(EC.number_of_windows_to_be(
                len(self.driver.window_handles)))

            new_window = None
            for window_handle in self.driver.window_handles:
                if window_handle != original_window:
                    new_window = window_handle
                    break

            if new_window:
                self.driver.switch_to.window(new_window)
                print(f"Switched to new tab: {new_window}")
                time.sleep(1)
                return new_window
            else:
                print("Error: Could not find the new window handle.")
                return None
        except Exception as e:
            print(
                f"Error opening or switching to new tab with URL {listing_url}: {e}")
            return None

    def close_current_tab_and_switch_back(self, original_handle: str):
        """Closes the current tab and switches back to the specified original tab handle."""
        if not self.driver or not original_handle:
            print(
                "Warning: Driver not initialized or original handle missing, cannot switch tabs.")
            return

        current_handle = self.driver.current_window_handle
        if current_handle == original_handle:
            print("Warning: Attempting to close the original tab. Aborting close.")
            return

        try:
            self.driver.close()
            print(f"Closed tab: {current_handle}")
            self.driver.switch_to.window(original_handle)
            print(f"Switched back to original tab: {original_handle}")
        except Exception as e:
            print(
                f"Error closing tab {current_handle} or switching back to {original_handle}: {e}")
            try:
                self.driver.switch_to.window(original_handle)
            except Exception as switch_e:
                print(
                    f"Could not switch back to original handle after error: {switch_e}")

    def _handle_onesignal_popup(self):
        """Checks for and closes the OneSignal slidedown popup if present."""
        try:
            popup_container_selector = (By.ID, "onesignal-slidedown-container")
            popup_container = WebDriverWait(self.driver, 3).until(
                EC.visibility_of_element_located(popup_container_selector)
            )
            print("OneSignal popup detected. Attempting to close...")

            possible_button_selectors = [
                (By.CSS_SELECTOR, "button.onesignal-slidedown-cancel-button"), 
                (By.ID, "onesignal-slidedown-cancel-button"),         
                (By.XPATH, ".//button[contains(text(), 'Later')]"),
                (By.XPATH, ".//button[contains(text(), 'No Thanks')]"),
            ]
            close_button = None
            for selector_type, selector_value in possible_button_selectors:
                try:
                    close_button = WebDriverWait(popup_container, 2).until(
                        EC.element_to_be_clickable(
                            (selector_type, selector_value))
                    )
                    print(
                        f"Found close button using: {selector_type}={selector_value}")
                    break
                except TimeoutException:
                    continue

            if close_button:
                self.driver.execute_script(
                    "arguments[0].click();", close_button)
                WebDriverWait(self.driver, 5).until( 
                    EC.invisibility_of_element_located(
                        popup_container_selector)
                )
                print("OneSignal popup closed.")
                time.sleep(0.5)
            else:
                print(
                    "Could not find a clickable close button within the OneSignal popup using known selectors.")

        except TimeoutException:
            pass
        except Exception as e:
            print(
                f"An error occurred while trying to close the OneSignal popup: {e}")

    def go_to_next_page(self) -> bool:
        """Clicks the 'Next' button if available and enabled. Returns True if successful, False otherwise."""
        if not self.driver:
            raise WebDriverException("WebDriver not initialized.")

        self._handle_onesignal_popup()

        next_button_selector = (
            By.CSS_SELECTOR, "li.next_page:not(.disabled) a[rel='next']")
        disabled_next_selector = (By.CSS_SELECTOR, "li.next_page.disabled")

        try:
            next_button = self.wait.until(
                EC.element_to_be_clickable(next_button_selector))
            current_url = self.driver.current_url

            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", next_button)
            time.sleep(0.5)

            try:
                next_button.click()
                print("Clicked 'Next' button directly.")
            except ElementClickInterceptedException as e:
                print(
                    f"Direct click intercepted for 'Next' button: {e}. Trying JavaScript click.")
                try:
                    self.driver.execute_script(
                        "arguments[0].click();", next_button)
                    print("Clicked 'Next' button via JavaScript.")
                except Exception as js_e:
                    print(
                        f"JavaScript click also failed for 'Next' button: {js_e}")
                    return False

            try:
                self.wait.until(EC.url_changes(current_url))
                print("URL changed after clicking Next.")
            except TimeoutException:
                print(
                    "URL did not change, waiting for listings to potentially reload...")
                try:
                    listing_on_current_page = self.driver.find_element(
                        By.CSS_SELECTOR, "li.classified-listing")
                    self.wait.until(EC.staleness_of(listing_on_current_page))
                    self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "li.classified-listing")))
                    print("Listings appear to have reloaded.")
                except (TimeoutException, NoSuchElementException):
                    print("Warning: Could not confirm page update after clicking Next.")

            return True

        except TimeoutException:
            try:
                self.driver.find_element(*disabled_next_selector)
                print("No enabled 'Next' button found (likely last page).")
            except NoSuchElementException:
                print(
                    "Error: 'Next' button not found or not clickable within timeout, and not disabled.")
            return False
        except Exception as e:
            print(f"An unexpected error occurred clicking 'Next' button: {e}")
            return False

    def go_to_previous_page(self):
        """Clicks the 'Previous' button to navigate to the previous page of listings."""
        if not self.driver:
            raise WebDriverException("WebDriver not initialized.")
        prev_button_selector = (
            By.CSS_SELECTOR, "li.prev:not(.disabled) a[rel='prev']")
        try:
            prev_button = self.wait.until(
                EC.element_to_be_clickable(prev_button_selector))
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", prev_button)
            time.sleep(0.5)
            prev_button.click()
            print("Clicked 'Previous' button.")
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "li.classified-listing")))
            print("Previous page loaded successfully.")
        except TimeoutException:
            print("Error: 'Previous' button not found or not clickable within timeout.")
        except Exception as e:
            print(f"Error clicking 'Previous' button: {e}")

    def go_to_page(self, page_number: int):
        """Navigates to a specific page number in the search results via URL."""
        if not self.driver:
            raise WebDriverException("WebDriver not initialized.")
        search_url = self.config.get("search_url", "")
        if not search_url:
            raise ValueError("Base URL not found in configuration.")
        if '?' in search_url:
            page_url = f"{search_url}&page={page_number}"
        else:
            if not search_url.endswith('/'):
                search_url += '/'
            page_url = f"{search_url}?page={page_number}"

        try:
            current_url = self.driver.current_url
            if current_url == page_url:
                print(f"Already on page {page_number}.")
                return

            self.driver.get(page_url)
            print(f"Navigated to page {page_number}: {page_url}")
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "li.classified-listing")))
            print(f"Page {page_number} loaded successfully.")
        except TimeoutException:
            print(
                f"Error: Timed out waiting for listings on page {page_number}.")
        except Exception as e:
            print(f"Error navigating to page {page_number}: {e}")

    def go_to_comparison_page(self):
        """Navigates to the base comparison URL specified in the config."""
        if not self.driver:
            raise WebDriverException(
                "WebDriver not initialized. Call initialize_driver() first.")
        comparison_url = self.config.get("comparison_url")
        if not comparison_url:
            raise ValueError("Base URL not found in configuration.")
        try:
            self.driver.get(comparison_url)
            print(f"Navigated to comparison page: {comparison_url}")
        except Exception as e:
            print(f"Error navigating to {comparison_url}: {e}")
            self.close_driver()
            raise
        
    def is_on_comparison_page(self) -> bool:
        """Checks if the current page is the comparison page."""
        if not self.driver:
            raise WebDriverException("WebDriver not initialized.")
        current_url = self.driver.current_url
        comparison_url = self.config.get("comparison_url")
        return comparison_url in current_url
    
    def is_on_search_page(self) -> bool:
        """Checks if the current page is the search page."""
        if not self.driver:
            raise WebDriverException("WebDriver not initialized.")
        current_url = self.driver.current_url
        search_url = self.config.get("search_url")
        return search_url in current_url

    def close_driver(self):
        """Closes the WebDriver."""
        if self.driver:
            try:
                print("Attempting to quit WebDriver.")
                self.driver.quit()
                print("WebDriver quit successfully.")
                self.driver = None
                self.wait = None
            except Exception as e:
                print(f"Error quitting WebDriver: {e}")
