import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException, ElementClickInterceptedException
from .extractor import ListingExtractor
from .models import ListingData
from typing import List


class FilterInteractor:
    """Handles interactions with filter elements on the search results page."""

    def __init__(self, driver: WebDriver, wait: WebDriverWait, navigator):
        """
        Initializes the FilterInteractor.

        Args:
            driver: The Selenium WebDriver instance.
            wait: The Selenium WebDriverWait instance.
        """
        self.driver = driver
        self.wait = wait
        self.navigator = navigator

    def _handle_onesignal_popup(self):
        """Checks for and closes the OneSignal slidedown popup if present."""
        try:
            popup_container = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located(
                    (By.ID, "onesignal-slidedown-container"))
            )
            print("OneSignal popup detected. Attempting to close...")
            close_button = popup_container.find_element(
                By.CSS_SELECTOR, "button.onesignal-slidedown-cancel-button")
            close_button.click()
            WebDriverWait(self.driver, 5).until(
                EC.invisibility_of_element_located(
                    (By.ID, "onesignal-slidedown-container"))
            )
            print("OneSignal popup closed.")
            time.sleep(0.5)
        except TimeoutException:
            print("OneSignal popup not found or did not appear within timeout.")
        except NoSuchElementException:
            print("Could not find the close button within the OneSignal popup.")
        except Exception as e:
            print(
                f"An error occurred while trying to close the OneSignal popup: {e}")

    def _find_filter_group_element(self, filter_name: str) -> WebElement | None:
        """Finds the main container element for a given filter category name."""
        try:
            heading_xpath = f"//div[contains(@class, 'accordion-heading')][.//a[normalize-space()='{filter_name}']]"
            heading_element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, heading_xpath)))
            filter_group = heading_element.find_element(
                By.XPATH, "./ancestor::div[contains(@class, 'accordion-group')]")
            return filter_group
        except (NoSuchElementException, TimeoutException):
            print(f"Error: Filter group '{filter_name}' not found.")
            return None

    def expand_accordion(self, filter_name: str):
        """
        Expands the accordion for a given filter category if it's collapsed.

        Args:
            filter_name: The exact text name of the filter category (e.g., 'Price Range').
        """
        filter_group = self._find_filter_group_element(filter_name)
        if not filter_group:
            return

        try:
            toggle_link = filter_group.find_element(
                By.XPATH, ".//div[contains(@class, 'accordion-heading')]//a[contains(@class, 'accordion-toggle')]")
            accordion_body = filter_group.find_element(
                By.XPATH, ".//div[contains(@class, 'accordion-body')]")

            is_collapsed = "collapse" == accordion_body.get_attribute("class").strip() or \
                           "0px" in accordion_body.get_attribute("style") or \
                           "collapsed" in toggle_link.get_attribute(
                               "class")

            if is_collapsed:
                print(f"Filter '{filter_name}' is collapsed, expanding...")
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", toggle_link)
                    time.sleep(0.5)
                    toggle_link.click()
                    self.wait.until(
                        lambda d: accordion_body.is_displayed(
                        ) and "in" in accordion_body.get_attribute("class")
                    )
                    print(f"Filter '{filter_name}' expanded.")
                    time.sleep(0.3)
                except (ElementNotInteractableException, ElementClickInterceptedException) as click_err:
                    print(
                        f"Warning: Toggle link for '{filter_name}' not interactable/intercepted ({type(click_err).__name__}). Trying JavaScript click.")
                    self.driver.execute_script(
                        "arguments[0].click();", toggle_link)
                    self.wait.until(
                        lambda d: accordion_body.is_displayed(
                        ) and "in" in accordion_body.get_attribute("class")
                    )
                    print(f"Filter '{filter_name}' expanded via JS click.")
                    time.sleep(0.3)

            else:
                print(f"Filter '{filter_name}' is already expanded.")

        except (NoSuchElementException, TimeoutException) as e:
            print(f"Error interacting with accordion for '{filter_name}': {e}")
        except Exception as e:
            print(
                f"An unexpected error occurred during accordion expansion for '{filter_name}': {e}")

    def open_more_choices_popup(self, filter_name: str) -> bool:
        filter_group = self._find_filter_group_element(filter_name)
        if not filter_group:
            return False

        try:
            more_choices_xpath = "./div[contains(@class, 'accordion-body')]//span[contains(@class, 'more-choice')]"
            print(
                f"Looking for 'More Choices' span using STRICT relative XPath: {more_choices_xpath} within filter '{filter_name}'")

            more_choices_span = filter_group.find_element(
                By.XPATH, more_choices_xpath)

            if not more_choices_span.is_displayed():
                time.sleep(0.5)
                if not more_choices_span.is_displayed():
                    print(
                        f"'More Choices' span found for '{filter_name}' but it is not visible.")
                    return False

            print(
                f"Found visible 'More Choices' span for '{filter_name}'. Clicking...")
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", more_choices_span)
            time.sleep(0.5)

            try:
                self.driver.execute_script(
                    "arguments[0].click();", more_choices_span)
                print("'More Choices' span clicked via JS.")
            except Exception as js_click_err:
                print(
                    f"JS click failed for 'More Choices': {js_click_err}. Trying direct click.")
                more_choices_span.click()

            popup_container_selector = (By.CSS_SELECTOR, "div.modal.in")
            print(
                f"Waiting for popup container with selector: {popup_container_selector}")
            self.wait.until(EC.visibility_of_element_located(
                popup_container_selector))
            print("'More Choices' popup opened and container is visible.")
            return True

        except NoSuchElementException:
            print(
                f"'More Choices' span not found within '{filter_name}' group body using relative XPath.")
            return False
        except TimeoutException as e:
            print(
                f"Error waiting for 'More Choices' popup for '{filter_name}': {e}")
            return False
        except ElementNotInteractableException as e:
            print(
                f"Error: 'More Choices' span for '{filter_name}' was not interactable: {e}")
            return False
        except Exception as e:
            print(
                f"An unexpected error occurred opening 'More Choices' for '{filter_name}': {e}")
            return False

    def verify_url_change(self, action_func, *args, **kwargs) -> bool:
        """
        Executes a given action function and verifies if the browser URL changes afterwards.

        Args:
            action_func: The function to call that should trigger a URL change
                         (e.g., self.select_filter_option).
            *args: Positional arguments to pass to action_func.
            **kwargs: Keyword arguments to pass to action_func.

        Returns:
            True if the URL changed after the action, False otherwise.
        """
        initial_url = self.driver.current_url
        print(f"Initial URL: {initial_url}")

        try:
            action_func(*args, **kwargs)

            self.wait.until(EC.url_changes(initial_url))
            final_url = self.driver.current_url
            print(f"URL changed successfully to: {final_url}")
            return True

        except TimeoutException:
            final_url = self.driver.current_url
            if initial_url == final_url:
                print("Error: URL did not change after the action.")
            else:
                print(
                    f"Warning: URL change wait timed out, but URL is now different: {final_url}")
                return True
            return False
        except Exception as e:
            print(
                f"An error occurred during the action or URL verification: {e}")
            return False

    def select_filter_option(self, filter_name: str, option_text: str):
        """
        Selects a specific option within a filter category.
        Handles expanding the accordion and opening 'More Choices' if necessary.

        Args:
            filter_name: The name of the filter category (e.g., 'Make').
            option_text: The exact text of the option to select (e.g., 'Toyota').
        """
        
        self.navigator._close_google_signin_popup(timeout=2)

        print(
            f"Attempting to select '{option_text}' in filter '{filter_name}'...")

        filter_group = self._find_filter_group_element(filter_name)
        if not filter_group:
            print(
                f"Cannot select option: Filter group '{filter_name}' not found.")
            return

        self.expand_accordion(filter_name)

        option_xpath = f""".//label[starts-with(normalize-space(.), '{option_text}')] |
                        .//a[starts-with(normalize-space(.), '{option_text}')] |
                        .//a//p[normalize-space(text()) = '{option_text}']"""

        option_element = None
        found_in_popup = False

        try:
            accordion_body = filter_group.find_element(
                By.XPATH, ".//div[contains(@class, 'accordion-body')]")
            possible_elements = accordion_body.find_elements(
                By.XPATH, option_xpath)
            if possible_elements:
                visible_elements = [
                    el for el in possible_elements if el.is_displayed()]
                print(
                    f"Found {len(possible_elements)} possible elements for '{option_text}' in '{filter_name}'.")
                if visible_elements:
                    option_element = visible_elements[0]
                    print(
                        f"Option '{option_text}' found directly in '{filter_name}'.")
                else:
                    option_element = possible_elements[0]
                    print(
                        f"Option '{option_text}' found directly (but hidden) in '{filter_name}'.")

        except NoSuchElementException:
            print(
                f"Option '{option_text}' not found directly in '{filter_name}'. Checking 'More Choices'.")
            pass

        if not option_element:
            print(
                f"Option '{option_text}' not found directly. Attempting to open 'More Choices' for '{filter_name}'.")
            try:
                if self.open_more_choices_popup(filter_name):
                    visible_modal_body_selector = (
                        By.CSS_SELECTOR, "div.modal.in .modal-body")
                    try:
                        popup_element = self.wait.until(
                            EC.visibility_of_element_located(
                                visible_modal_body_selector),
                            message=f"Timed out waiting for visible modal body '{visible_modal_body_selector}' after popup open."
                        )
                        print(
                            f"Searching within visible modal body ({visible_modal_body_selector})...")
                        possible_elements_popup = popup_element.find_elements(
                            By.XPATH, option_xpath)
                        if possible_elements_popup:
                            visible_elements_popup = [
                                el for el in possible_elements_popup if el.is_displayed()]
                            if visible_elements_popup:
                                option_element = visible_elements_popup[0]
                                print(
                                    f"Option '{option_text}' found in 'More Choices' popup for '{filter_name}'.")
                                found_in_popup = True
                            else:
                                option_element = possible_elements_popup[0]
                                print(
                                    f"Option '{option_text}' found (but hidden) in 'More Choices' popup for '{filter_name}'.")
                        else:
                            print(
                                f"Option '{option_text}' not found within the visible modal body.")

                    except TimeoutException as e:
                        print(
                            f"Error finding or searching within visible modal body: {e}")
                    except NoSuchElementException:
                        print(
                            f"Error: Could not find visible modal body using selector '{visible_modal_body_selector}'.")

                else:
                    print(
                        f"Option '{option_text}' not found, and 'More Choices' could not be opened or does not exist for '{filter_name}'.")

            except Exception as e:
                print(
                    f"An unexpected error occurred while trying to handle 'More Choices' for '{filter_name}': {e}")

        if option_element:
            try:
                self.navigator._handle_onesignal_popup()
                try:
                    modal_container = self.driver.find_element(
                        By.CSS_SELECTOR, "div.modal.more_choices")
                    if modal_container.is_displayed():
                        print("Filter modal detected. Attempting to submit...")

                        submit_button_selectors = [
                            (By.CSS_SELECTOR,
                             "button.btn-primary[value='submit']"),
                            (By.CSS_SELECTOR,
                             "button.btn-primary[type='button']"),
                            (By.XPATH,
                             ".//button[contains(@class, 'btn-primary') and contains(text(), 'Submit')]"),
                            (By.XPATH,
                             ".//button[contains(@class, 'btn-primary') and @value='submit']"),
                            (By.XPATH,
                             ".//button[contains(@onclick, 'doSubmit')]")
                        ]

                        submit_button = None
                        for selector_type, selector_value in submit_button_selectors:
                            try:
                                submit_button = modal_container.find_element(
                                    selector_type, selector_value)
                                if submit_button.is_displayed():
                                    print(
                                        f"Found submit button with selector: {selector_type}={selector_value}")
                                    break
                            except NoSuchElementException:
                                continue

                        if submit_button and submit_button.is_displayed():
                            try:
                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView(true);", submit_button)
                                time.sleep(0.5)

                                self.driver.execute_script(
                                    "arguments[0].click();", submit_button)
                                print("Clicked Submit button in the filter modal.")

                                try:
                                    WebDriverWait(self.driver, 10).until(
                                        lambda d: d.find_element(
                                            By.CSS_SELECTOR, "div.ajax-loading").get_attribute("style") == "display: none;"
                                    )
                                except Exception:
                                    print(
                                        "Warning: AJAX loading indicator not found or didn't disappear.")

                                time.sleep(2)
                            except Exception as submit_e:
                                print(
                                    f"Warning: Failed to click Submit button: {submit_e}")
                        else:
                            print(
                                "Warning: Could not find a visible Submit button in the modal.")
                except NoSuchElementException:
                    pass
                except Exception as popup_e:
                    print(
                        f"Warning: Error handling OneSignal popup: {popup_e}")

                self.driver.execute_script(
                    "arguments[0].scrollIntoView(true);", option_element)
                time.sleep(0.5)

                option_element.click()
                print(
                    f"Clicked option '{option_text}' in filter '{filter_name}'.")

            except ElementClickInterceptedException as e:
                print(
                    f"Error: Click still intercepted for '{option_text}' even after popup handling attempt: {e}")
                print("Trying JavaScript click as a fallback...")
                try:
                    self.driver.execute_script(
                        "arguments[0].click();", option_element)
                    print(f"Clicked option '{option_text}' using JavaScript.")
                except Exception as js_e:
                    print(
                        f"Error: JavaScript click also failed for option '{option_text}': {js_e}")
                    return

            if found_in_popup:
                print(
                    "Option was selected in 'More Choices' popup. Attempting to click Submit.")
                try:
                    visible_modal_selector = (By.CSS_SELECTOR, "div.modal.in")
                    modal_container = WebDriverWait(self.driver, 5).until(
                        EC.visibility_of_element_located(
                            visible_modal_selector),
                        message="Could not find visible modal container (div.modal.in) before clicking Submit."
                    )

                    submit_button_selectors = [
                        (By.CSS_SELECTOR, ".modal-footer button.btn-primary"),
                        (By.XPATH, ".//button[contains(text(), 'Submit')]"),
                        (By.XPATH,
                         ".//button[contains(@class, 'btn-primary')]"),
                        (By.CSS_SELECTOR, "button[type='submit']"),
                        (By.CSS_SELECTOR, "button[value='submit']")
                    ]
                    submit_button = None
                    for selector_type, selector_value in submit_button_selectors:
                        try:
                            submit_button = modal_container.find_element(
                                selector_type, selector_value)
                            if submit_button.is_displayed():
                                print(
                                    f"Found visible Submit button using: {selector_type}={selector_value}")
                                break
                        except NoSuchElementException:
                            continue

                    if submit_button and submit_button.is_displayed():
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView(true);", submit_button)
                        time.sleep(0.5)
                        self.driver.execute_script(
                            "arguments[0].click();", submit_button)
                        print("Clicked Submit button via JS.")
                        try:
                            WebDriverWait(self.driver, 10).until(
                                EC.invisibility_of_element_located(
                                    visible_modal_selector)
                            )
                            print("Modal closed after submit.")
                        except TimeoutException:
                            print(
                                "Warning: Modal did not close automatically after submit, or timeout occurred.")
                        time.sleep(1)
                    else:
                        print(
                            "Warning: Could not find a visible Submit button in the 'More Choices' popup footer.")

                except (NoSuchElementException, TimeoutException) as submit_err:
                    print(
                        f"Error finding or clicking the Submit button: {submit_err}")
                except Exception as submit_e:
                    print(
                        f"An unexpected error occurred while handling Submit button: {submit_e}")

        else:
            print(
                f"Error: Could not find the option '{option_text}' for filter '{filter_name}' after checking direct view and 'More Choices'.")

    def apply_range_filter(self, filter_name: str, min_value: int | str | None = None, max_value: int | str | None = None):
        """
        Applies a range filter (e.g., Price Range, Year) by entering min/max values and clicking 'Go'.

        Args:
            filter_name: The name of the range filter (e.g., 'Price Range').
            min_value: The minimum value to enter (optional).
            max_value: The maximum value to enter (optional).
        """
        self.navigator._close_google_signin_popup(timeout=2)

        print(
            f"Attempting to apply range filter '{filter_name}' with min='{min_value}', max='{max_value}'...")

        filter_group = self._find_filter_group_element(filter_name)
        if not filter_group:
            print(
                f"Cannot apply range filter: Filter group '{filter_name}' not found.")
            return

        self.expand_accordion(filter_name)

        try:
            accordion_body = filter_group.find_element(
                By.XPATH, ".//div[contains(@class, 'accordion-body')]")

            # --- Find Input Fields ---
            from_input = None
            to_input = None
            go_button = None

            try:
                filter_prefix = "".join(word[0]
                                        for word in filter_name.split()).lower()
                from_input = accordion_body.find_element(
                    By.CSS_SELECTOR, f"input[id='{filter_prefix}_from']")
                to_input = accordion_body.find_element(
                    By.CSS_SELECTOR, f"input[id='{filter_prefix}_to']")
                print(
                    f"Found range inputs by specific ID prefix: '{filter_prefix}'")
            except NoSuchElementException:
                print(
                    f"Could not find range inputs by specific ID prefix '{filter_prefix}', trying placeholders...")
                try:
                    from_input = accordion_body.find_element(
                        By.CSS_SELECTOR, "input[placeholder='From']")
                    to_input = accordion_body.find_element(
                        By.CSS_SELECTOR, "input[placeholder='To']")
                    print("Found range inputs by placeholder.")
                except NoSuchElementException:
                    print(
                        f"Error: Could not find 'From' or 'To' input fields for filter '{filter_name}' using common methods.")
                    return

            # --- Find Go Button ---
            try:
                filter_prefix = "".join(word[0]
                                        for word in filter_name.split()).lower()
                go_button = accordion_body.find_element(
                    By.CSS_SELECTOR, f"input[type='submit'][id='{filter_prefix}-go']")
                print(f"Found Go button by specific ID: '{filter_prefix}-go'")
            except NoSuchElementException:
                print(
                    "Could not find Go button by specific ID, trying generic value='Go'...")
                try:
                    go_button = accordion_body.find_element(
                        By.CSS_SELECTOR, "input[type='submit'][value='Go']")
                    print("Found Go button by value='Go'.")
                except NoSuchElementException:
                    print(
                        f"Error: Could not find the 'Go' button for filter '{filter_name}'.")
                    return

            # --- Enter Values ---
            if from_input and min_value is not None:
                try:
                    self.wait.until(EC.element_to_be_clickable(from_input))
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", from_input)
                    time.sleep(0.2)
                    from_input.clear()
                    from_input.send_keys(str(min_value))
                    print(f"Entered '{min_value}' into 'From' field.")
                except (ElementNotInteractableException, TimeoutException) as e:
                    print(
                        f"Warning: Could not interact with 'From' input: {e}")
                except Exception as e:
                    print(
                        f"Warning: Unexpected error interacting with 'From' input: {e}")

            if to_input and max_value is not None:
                try:
                    self.wait.until(EC.element_to_be_clickable(to_input))
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", to_input)
                    time.sleep(0.2)
                    to_input.clear()
                    to_input.send_keys(str(max_value))
                    print(f"Entered '{max_value}' into 'To' field.")
                except (ElementNotInteractableException, TimeoutException) as e:
                    print(f"Warning: Could not interact with 'To' input: {e}")
                except Exception as e:
                    print(
                        f"Warning: Unexpected error interacting with 'To' input: {e}")

            # --- Click Go Button ---
            if go_button:
                try:
                    self.wait.until(EC.element_to_be_clickable(go_button))
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", go_button)
                    time.sleep(0.3)
                    self.driver.execute_script(
                        "arguments[0].click();", go_button)
                    print(f"Clicked 'Go' button for filter '{filter_name}'.")
                    time.sleep(1)
                except (ElementNotInteractableException, TimeoutException) as e:
                    print(f"Error: 'Go' button not clickable: {e}")
                except Exception as e:
                    print(f"Error clicking 'Go' button: {e}")

        except NoSuchElementException as e:
            print(
                f"Error finding elements within the range filter '{filter_name}': {e}")
        except Exception as e:
            print(
                f"An unexpected error occurred while applying range filter '{filter_name}': {e}")

    def get_current_listings_data(self) -> List[ListingData]:
        """
        Finds all listing elements on the current page and extracts their data.

        Returns:
            A list of ListingData objects, one for each listing found.
        """
        listings_data = []
        extractor = ListingExtractor()
        try:
            listings_container_selector = (
                By.CSS_SELECTOR, "ul.search-results-mid")
            self.wait.until(EC.presence_of_element_located(
                listings_container_selector))
            time.sleep(1)

            listing_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "li.classified-listing")
            print(
                f"Found {len(listing_elements)} listing elements on the page.")

            for element in listing_elements:
                try:
                    data = extractor.extract_listing_data(element)
                    listings_data.append(data)
                except Exception as e:
                    listing_id = element.get_attribute(
                        'data-listing-id') or 'unknown'
                    print(
                        f"Warning: Failed to extract data for listing ID '{listing_id}': {e}")

        except TimeoutException:
            print(
                "Warning: Timed out waiting for listings container or no listings found.")
        except Exception as e:
            print(f"An error occurred while fetching listing elements: {e}")

        return listings_data

    def sleep_driver(self, seconds: int = 1):
        """
        Pauses the WebDriver for a specified number of seconds.

        Args:
            seconds: The number of seconds to sleep (default is 1).
        """
        if self.driver:
            print(f"Sleeping WebDriver for {seconds} seconds...")
            time.sleep(seconds)
        else:
            print("Warning: WebDriver not initialized. Cannot sleep.")

    def create_filter_query_string(self, filters_dict):
        """
        Creates a single query string from a dictionary of applied filters,
        always placing the city last with a preceding 'in'.
        """
        parts = []
        city = None

        for key, value in filters_dict.items():
            if not (isinstance(value, dict) and "type" in value and "value" in value):
                continue

            if key.lower() == "city" and value["type"] == "option" and value["value"]:
                city = value["value"]
            else:
                if value["type"] == "option" and value["value"]:
                    parts.append(f"{value['value']}")
                elif value["type"] == "range":
                    min_str = value.get("min", "")
                    max_str = value.get("max", "")
                    parts.append(f"{key} {min_str}-{max_str}")

        search_query = " ".join(parts).strip()

        if city:
            if search_query:
                search_query += f" in {city}"
            else:
                search_query = f"in {city}"

        return search_query

    def _normalize_filter_dict(self, filters: dict[str, str]) -> dict:
        return {k: {"type": "option", "value": v} for k, v in filters.items() if v}

    def enter_text_search(self, filters: dict[str, str]):
        """
        Enters a text search in the search bar and submits the form.
        """
        print("Entering text search...")

        try:
            modal = self.driver.find_element(
                By.CSS_SELECTOR, "div.modal.in, div.modal.show")
            close_btn = modal.find_element(
                By.CSS_SELECTOR, ".close, .modal-header .close")
            close_btn.click()
            print("Closed blocking modal.")
            self.wait.until(EC.invisibility_of_element(modal))
        except NoSuchElementException:
            pass

        try:
            search_input = self.wait.until(
                EC.element_to_be_clickable((By.ID, "q"))
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", search_input
            )
        except TimeoutException as e:
            print(f"Error: search input not ready: {e}")
            raise

        keyword = self._normalize_filter_dict(filters)
        keyword = self.create_filter_query_string(keyword)

        if keyword:
            search_input.clear()
            search_input.send_keys(keyword)
            print(f"Entered keyword: {keyword}")
        else:
            print("No keyword provided; skipping input entry.")

        query = self.create_filter_query_string(
            self._normalize_filter_dict(filters))
        try:
            qp = self.driver.find_element(By.ID, "query_params")
            self.driver.execute_script(
                "arguments[0].value = arguments[1];", qp, query)
            print(f"Set hidden query_params to: {query}")
        except NoSuchElementException:
            pass

        try:
            submit_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input.refine-go"))
            )
            submit_btn.click()
            print("Search submitted; waiting for results…")
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".search-results")))
        except Exception as e:
            print(f"Error submitting search: {e}")
            raise

    """Only 4 options are available in the dropdown with 2 sub options:
    - Updated Date: Recent First
    - Updated Date: Oldest First
    - Price: Low to High
    - Price: High to Low
    - Model Year: Latest First
    - Model Year: Oldest First
    - Mileage: Low to High
    - Mileage: High to Low"""

    def apply_sort(self, sort_option: str):
        """
        Applies a sorting option from the dropdown menu.

        Args:
            sort_option: The sorting option to apply (e.g., 'Updated Date: Recent First').
        """
        print(f"Applying sort option: {sort_option}")

        try:
            sort_dropdown = self.wait.until(
                EC.element_to_be_clickable((By.ID, "sortby"))
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", sort_dropdown
            )
            time.sleep(0.5)
        except TimeoutException as e:
            print(f"Error: Sort dropdown not ready: {e}")
            return

        try:
            sort_dropdown.click()
            time.sleep(0.5)
        except Exception as e:
            print(f"Error clicking sort dropdown: {e}")
            return

        try:
            options = sort_dropdown.find_elements(By.TAG_NAME, "option")
            for option in options:
                if option.text == sort_option:
                    option.click()
                    print(f"Clicked sort option: {sort_option}")
                    break
            else:
                print(f"Sort option '{sort_option}' not found.")
        except Exception as e:
            print(f"Error selecting sort option: {e}")
