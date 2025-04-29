from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from .models import *
import re
from selenium.webdriver.remote.webdriver import WebDriver
import json
from typing import Any, Tuple

class ListingExtractor:
    """Extracts structured data from listing elements."""

    def _safe_find_text(self, element: WebElement, by: By, value: str) -> str | None:
        """Safely finds an element and returns its text, handling NoSuchElementException."""
        try:
            return element.find_element(by, value).text.strip()
        except NoSuchElementException:
            return None

    def _parse_price(self, price_str: str | None) -> int | None:
        """Parses price string like 'PKR 1,096,470,000' or 'PKR 16.8 lacs' into an integer."""
        if not price_str:
            return None
        
        price_str_cleaned = price_str.lower().replace('pkr', '').replace(',', '').strip()
        
        num_part = re.match(r'([\d.]+)', price_str_cleaned)
        if not num_part:
            return None

        try:
            num = float(num_part.group(1))
        except ValueError:
            return None 

        if 'lacs' in price_str_cleaned or 'lac' in price_str_cleaned:
            return int(num * 100000)
        elif 'crore' in price_str_cleaned or 'cr' in price_str_cleaned:
            return int(num * 10000000)
        else:
            return int(num)

    def _parse_mileage(self, mileage_str: str | None) -> int | None:
        """Parses mileage string like '109,877 km' into an integer."""
        if not mileage_str:
            return None
        num_part = re.search(r'[\d,]+', mileage_str)
        if num_part:
            return int(num_part.group(0).replace(',', ''))
        return None

    def _parse_engine_capacity(self, capacity_str: str | None) -> int | None:
        """Parses engine capacity string like '1600 cc' into an integer."""
        if not capacity_str:
            return None
        num_part = re.search(r'\d+', capacity_str)
        if num_part:
            return int(num_part.group(0))
        return None

    def _parse_picture_count(self, count_str: str | None) -> int:
        """Parses picture count string like '13' into an integer."""
        if not count_str:
            return 0
        num_part = re.search(r'\d+', count_str)
        if num_part:
            return int(num_part.group(0))
        return 0

    def extract_listing_data(self, listing_element: WebElement) -> ListingData:
        """
        Extracts data from a single listing WebElement.

        Args:
            listing_element: The WebElement representing the listing container 
                             (e.g., the <li> with class 'classified-listing').

        Returns:
            A ListingData object populated with extracted information.
        """
        data = ListingData()

        # --- Basic Info ---
        data.listing_id = listing_element.get_attribute('data-listing-id')

        try:
            car_link_element = listing_element.find_element(
                By.CSS_SELECTOR, 'a.car-name.ad-detail-path')
            data.url = car_link_element.get_attribute('href')
        except NoSuchElementException:
            data.url = None

        # --- Price ---
        price_text = self._safe_find_text(
            listing_element, By.CSS_SELECTOR, '.price-details')
        data.price = self._parse_price(price_text)

        # --- Location ---
        data.city = self._safe_find_text(
            listing_element, By.CSS_SELECTOR, '.search-vehicle-info li:first-child')

        # --- Specs (using the second ul) ---
        specs_elements = listing_element.find_elements(
            By.CSS_SELECTOR, '.search-vehicle-info-2 li')

        if len(specs_elements) >= 1:
            data.year = specs_elements[0].text.strip()
        if len(specs_elements) >= 2:
            data.mileage = self._parse_mileage(specs_elements[1].text)
        if len(specs_elements) >= 3:
            data.engine_type = specs_elements[2].text.strip()
        if len(specs_elements) >= 4:
            data.engine_capacity = self._parse_engine_capacity(
                specs_elements[3].text)
        if len(specs_elements) >= 5:
            data.transmission = specs_elements[4].text.strip()

        # --- Pictures ---
        pic_count_text = self._safe_find_text(
            listing_element, By.CSS_SELECTOR, '.total-pictures-bar')
        data.picture_count = self._parse_picture_count(pic_count_text)
        data.picture_availability = data.picture_count > 0

        return data

    def _parse_location(self, location_str: str | None) -> tuple[str | None, str | None, str | None]:
        """Parses location string like 'Kemari Town, Karachi Sindh' into area, city, province."""
        if not location_str:
            return None, None, None

        parts = [part.strip() for part in location_str.split(',')]
        if len(parts) == 3:  # Area, City, Province
            return parts[0], parts[1], parts[2]
        elif len(parts) == 2:  # City, Province 
            return None, parts[0], parts[1]
        elif len(parts) == 1:  # Assume City 
            provinces = ["sindh", "punjab", "balochistan",
                         "khyber pakhtunkhwa", "gilgit-baltistan", "azad kashmir"]
            if parts[0].lower() in provinces:
                return None, None, parts[0]
            else:
                return None, parts[0], None
        return None, None, None  

    def _extract_from_ul_featured(self, driver) -> dict:
        """Extracts key-value pairs from the 'ul-featured' list."""
        data = {}
        try:
            ul_element = driver.find_element(By.CSS_SELECTOR, "ul.ul-featured")
            list_items = ul_element.find_elements(By.TAG_NAME, "li")
            for i in range(0, len(list_items), 2):
                if i + 1 < len(list_items):
                    key_element = list_items[i]
                    value_element = list_items[i+1]
                    if "ad-data" in key_element.get_attribute("class"):
                        key = key_element.text.strip().replace(':', '') 
                        value = value_element.text.strip()
                        data[key] = value
        except NoSuchElementException:
            print("Warning: Could not find 'ul-featured' list for detailed specs.")
        except Exception as e:
            print(f"Warning: Error parsing 'ul-featured' list: {e}")
        return data

    def extract_listing_page_data(self, driver) -> ListingPageData:
        """
        Extracts detailed data from the listing detail page WebElement.

        Args:
            driver: The Selenium WebDriver instance currently on the detail page.

        Returns:
            A ListingPageData object populated with extracted information.
        """
        data = ListingPageData()
        json_ld_data = {}

        try:
            json_ld_script = driver.find_element(
                By.XPATH, "//script[@type='application/ld+json']")
            json_ld_content = json_ld_script.get_attribute('innerHTML')
            json_ld_data = json.loads(json_ld_content)
            print("Successfully parsed JSON-LD data.")
        except NoSuchElementException:
            print("Warning: JSON-LD script not found.")
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to decode JSON-LD: {e}")
        except Exception as e:
            print(
                f"Warning: An unexpected error occurred parsing JSON-LD: {e}")

        try:
            if json_ld_data.get('offers') and 'price' in json_ld_data['offers']:
                data.price = int(json_ld_data['offers']['price'])
            else:
                price_text = self._safe_find_text(
                    driver, By.CSS_SELECTOR, '.price-box strong')
                if not price_text:
                    price_text = self._safe_find_text(
                        driver, By.CSS_SELECTOR, '.light-gallery-user-info strong.generic-white')
                data.price = self._parse_price(price_text)
        except Exception as e:
            print(f"Warning: Could not extract price: {e}")

        try:
            location_full = self._safe_find_text(
                driver, By.CSS_SELECTOR, 'p.detail-sub-heading a')
            if location_full:
                location_full = location_full.replace('map marker', '').strip()
                data.area, data.city, data.province = self._parse_location(
                    location_full)
        except Exception as e:
            print(f"Warning: Could not extract location: {e}")

        try:
            specs_table = driver.find_element(
                By.CSS_SELECTOR, "table.table-engine-detail")
            cells = specs_table.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 1:
                data.year = int(cells[0].text.strip(
                )) if cells[0].text.strip().isdigit() else None
            if len(cells) >= 2:
                data.mileage = self._parse_mileage(cells[1].text)
            if len(cells) >= 3:
                data.engine_type = cells[2].text.strip()
            if len(cells) >= 4:
                data.transmission = cells[3].text.strip()
        except NoSuchElementException:
            print("Warning: Could not find main specs table.")
        except Exception as e:
            print(f"Warning: Error parsing main specs table: {e}")

        # --- Specs from ul-featured ---
        ul_data = self._extract_from_ul_featured(driver)

        data.registered_in = ul_data.get('Registered In')
        data.colour = ul_data.get('Color')
        data.assembly = ul_data.get('Assembly')
        data.engine_capacity = self._parse_engine_capacity(ul_data.get(
            'Engine Capacity'))  
        data.body_type = ul_data.get('Body Type')
        data.last_updated = ul_data.get('Last Updated')
        data.ad_reference = ul_data.get('Ad Ref #')

        if json_ld_data:
            if 'modelDate' in json_ld_data:
                data.year = int(json_ld_data['modelDate'])
            if 'mileageFromOdometer' in json_ld_data:
                data.mileage = self._parse_mileage(
                    json_ld_data['mileageFromOdometer'])
            if 'fuelType' in json_ld_data:
                data.engine_type = json_ld_data['fuelType']
            if 'vehicleTransmission' in json_ld_data:
                data.transmission = json_ld_data['vehicleTransmission']
            if 'color' in json_ld_data:
                data.colour = json_ld_data['color']
            if json_ld_data.get('vehicleEngine') and 'engineDisplacement' in json_ld_data['vehicleEngine']:
                data.engine_capacity = self._parse_engine_capacity(
                    json_ld_data['vehicleEngine']['engineDisplacement'])

        try:
            contact_button = driver.find_element(
                By.CSS_SELECTOR, "button.phone_number_btn span")
            button_text = contact_button.text.strip()
            match = re.search(r'(\d+\.{3,})', button_text)
            if match:
                data.seller_contact = match.group(1)
            else:
                data.seller_contact = button_text.split(
                    '\n')[0].strip() if '\n' in button_text else None
        except NoSuchElementException:
            print("Warning: Could not find seller contact button.")
        except Exception as e:
            print(f"Warning: Error extracting seller contact: {e}")

        return data

    def _parse_comparison_value(self, td_element: WebElement) -> Any:
        """Parses the value from a comparison table cell (td)."""
        try:
            check_icon = td_element.find_elements(
                By.CSS_SELECTOR, "i.fa.fa-check")
            if check_icon:
                return True
            cross_icon = td_element.find_elements(
                By.CSS_SELECTOR, "i.fa.fa-times")
            if cross_icon:
                return False
            return td_element.text.strip()
        except NoSuchElementException:
            return td_element.text.strip()
        except Exception as e:
            print(f"Warning: Error parsing comparison cell value: {e}")
            return None 

    def _parse_review_count(self, review_text: str | None) -> int | None:
        """Parses review text like '4 Reviews' or '0 Reviews' into an integer."""
        if not review_text:
            return 0  
        match = re.search(r'(\d+)\s+Review', review_text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 0  

    def _parse_review_count(self, review_text: str | None) -> int | None:
        """Parses review text like '4 Reviews' or '0 Reviews' into an integer."""
        if not review_text:
            return 0 
        match = re.search(r'(\d+)\s+Review', review_text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 0 

    def _extract_review_info(self, driver: WebDriver, car_index: int) -> Tuple[int | None, int | None]:
        """
        Extracts rating (star count) and review count using absolute XPath templates 
        based on car index (0, 1, or 2).

        Args:
            driver: The Selenium WebDriver instance.
            car_index: The index of the car (0, 1, or 2) corresponding to td[2], td[3], td[4].

        Returns:
            A tuple containing (rating_stars, review_count).
        """
        rating_stars = None
        review_count = 0 
        
        td_index = car_index + 2 
        base_td_xpath = f'//*[@id="main-container"]/section[2]/div/form/table/tbody/tr[3]/td[{td_index}]'
        
        try:
            rating_cell = driver.find_element(By.XPATH, base_td_xpath)

            # --- Extract Rating Stars (relative to the found TD) ---
            try:
                filled_stars = rating_cell.find_elements(By.CSS_SELECTOR, "span.rating i.fa.fa-star")
                rating_stars = len(filled_stars)
            except Exception as e:
                print(f"Warning: Error parsing rating stars for car index {car_index}: {e}")

            # --- Extract Review Count (relative to the found TD) ---
            review_text_content = None
            try:
                try:
                    review_link = rating_cell.find_element(By.XPATH, ".//a[contains(text(), 'Review')]") 
                    review_text_content = review_link.text.strip()
                except NoSuchElementException:
                    xpath_text_node = ".//text()[normalize-space() and contains(lower-case(.), 'review')]"
                    try:
                        text_nodes = rating_cell.find_elements(By.XPATH, xpath_text_node)
                        if text_nodes:
                            for node_text in text_nodes:
                                cleaned_text = node_text.strip()
                                if cleaned_text:
                                    review_text_content = cleaned_text
                                    # print(f"  Found review count via text node for car {car_index}: {review_text_content}") # Debug
                                    break 

                    except Exception as text_e:
                        print(f"  Warning: Error searching for review text node for car index {car_index}: {text_e}")

                review_count = self._parse_review_count(review_text_content)

            except Exception as e:
                print(f"Warning: Error extracting review count text for car index {car_index}: {e}")
                review_count = None 

        except NoSuchElementException:
             print(f"Warning: Could not find the main TD element for car index {car_index} using XPath: {base_td_xpath}")
        except Exception as e:
             print(f"Warning: General error processing review info for car index {car_index}: {e}")
             rating_stars = None
             review_count = None

        return rating_stars, review_count


    def extract_comparison_data(self, driver: WebDriver) -> ComparisonResult:
        """
        Extracts structured data from the car comparison results page, 
        including header info and specification sections.

        Args:
            driver: The Selenium WebDriver instance on the comparison results page.

        Returns:
            A ComparisonResult object populated with the extracted data.
        """
        print("Extracting comparison data...")
        comparison_result = ComparisonResult()
        max_cars = 3 

        # --- Extract Header Information ---
        try:
            header_table = driver.find_element(
                By.CSS_SELECTOR, "table.vehicle-compare-head")
            
            header_rows = header_table.find_elements(By.XPATH, ".//tbody/tr")

            if len(header_rows) >= 3:
                name_row_cells = header_rows[0].find_elements(By.TAG_NAME, "td")[1:] 
                price_rating_review_row_cells = header_rows[2].find_elements(By.TAG_NAME, "td")[1:] 

                for i in range(max_cars):
                    
                    # Extract Name 
                    if i < len(name_row_cells):
                        try:
                            name = name_row_cells[i].find_element(By.TAG_NAME, "h3").text.strip()
                            comparison_result.car_names[i] = name
                        except NoSuchElementException:
                            print(f"Warning: Could not find name element for car index {i}.")
                            comparison_result.car_names[i] = None
                    else:
                        comparison_result.car_names[i] = None
                        comparison_result.prices[i] = None
                        comparison_result.ratings[i] = None
                        comparison_result.review_counts[i] = None
                        print(f"Info: No name cell found for car index {i}. Skipping further header extraction for this slot.")
                        continue

                    # Extract Price, Rating, Reviews (using index i for the cell list)
                    if i < len(price_rating_review_row_cells):
                        rating_cell = price_rating_review_row_cells[i]
                        
                        # Price
                        try:
                            price_text = rating_cell.find_element(By.CSS_SELECTOR, "strong.fs22").text.strip()
                            comparison_result.prices[i] = self._parse_price(price_text)
                        except NoSuchElementException:
                            comparison_result.prices[i] = None 
                            print(f"Info: Price element (strong.fs22) not found or empty for car index {i}.")
                        except Exception as e:
                            print(f"Warning: Error parsing price for car index {i}: {e}")
                            comparison_result.prices[i] = None

                        # Rating & Reviews
                        try:
                            rating, reviews = self._extract_review_info(driver, i) 
                            comparison_result.ratings[i] = rating
                            comparison_result.review_counts[i] = reviews
                        except Exception as e:
                            print(f"Warning: Error calling _extract_review_info for car index {i}: {e}")
                            comparison_result.ratings[i] = None
                            comparison_result.review_counts[i] = None
                    else:
                        comparison_result.prices[i] = None
                        comparison_result.ratings[i] = None
                        comparison_result.review_counts[i] = None
                        print(f"Warning: No price/rating/review cell found for car index {i}.")

            else:
                 print("Warning: Comparison header table does not have enough rows (expected >= 3).")


            print(
                f"  Extracted Header Info: Names={comparison_result.car_names}, Prices={comparison_result.prices}, Ratings={comparison_result.ratings}, Reviews={comparison_result.review_counts}")

        except NoSuchElementException:
            print(
                "Warning: Could not find comparison header table (table.vehicle-compare-head). Header data will be missing.")
        except Exception as e:
            print(f"Warning: An unexpected error occurred processing comparison header: {e}")


        # --- Extract Specification Sections (Existing Logic) ---
        section_wrappers = driver.find_elements(
            By.CSS_SELECTOR, "div.specs-wrapper.spec-compare-details")
        print(f"Found {len(section_wrappers)} comparison sections.")

        for wrapper in section_wrappers:
            try:
                section = ComparisonSection()

                # Extract section title
                title_element = wrapper.find_element(
                    By.CSS_SELECTOR, "h3.specs-heading")
                section.title = title_element.text.strip()
                if not section.title:
                    try:
                        nested_span = title_element.find_element(
                            By.TAG_NAME, "span")
                        section.title = nested_span.text.strip()
                    except NoSuchElementException:
                        pass

                print(f"  Processing section: {section.title}")

                table = wrapper.find_element(By.TAG_NAME, "table")
                rows = table.find_elements(By.XPATH, ".//tbody/tr")

                for row in rows:
                    spec = ComparisonSpec()
                    cells = row.find_elements(By.TAG_NAME, "td")

                    if not cells:
                        continue

                    feature_cell = cells[0]
                    spec.feature = feature_cell.text.strip()
                    if not spec.feature:
                        try:
                            nested_span = feature_cell.find_element(
                                By.TAG_NAME, "span")
                            spec.feature = nested_span.text.strip()
                        except NoSuchElementException:
                            pass

                    spec.values = [self._parse_comparison_value(
                        cell) for cell in cells[1:]]

                    if spec.feature:
                        section.specifications.append(spec)

                if section.title and section.specifications:
                    comparison_result.sections.append(section)

            except NoSuchElementException as e:
                print(
                    f"Warning: Skipping section '{section.title}' due to missing element: {e}")
            except Exception as e:
                print(
                    f"Warning: Error processing section '{section.title}': {e}")

        print("Comparison data extraction finished.")
        return comparison_result
