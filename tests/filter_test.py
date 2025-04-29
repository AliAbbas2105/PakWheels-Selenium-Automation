import unittest
from core.models import ListingPageData
from tests.base_test import BaseTest
from core.search_interactor import FilterInteractor
from core.extractor import ListingExtractor
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
from typing import List, Dict, Any, Callable, Tuple


class FilterTests(BaseTest):
    """Test suite for filter functionality."""

    def setUp(self):
        """Navigate to the search page before each test."""
        self.navigator.go_to_search_page()
        self.filter_interactor = FilterInteractor(
            self.driver, self.wait, self.navigator)  # Initialize interactor
        self.extractor = ListingExtractor()

    # --------------------------------------------------------------
    # Test Case 1: Test the search bar functionality
    # --------------------------------------------------------------
    def test_search_bar(self):
        print("\nRunning test: test_search_bar")
        filters = {
            "City": "Lahore",
            "Transmission": "Automatic"
        }

        self.filter_interactor.enter_text_search(filters)
        time.sleep(3)

        listings = self.filter_interactor.get_current_listings_data()

        self.assertGreater(len(
            listings), 0, "No listings found after applying filters. Check filter criteria or website state.")

        print(f"Verifying {len(listings)} listings against filters...")
        mismatches = []

        for i, listing in enumerate(listings):
            # Verify City
            if listing.city and filters["City"].lower() not in listing.city.lower():
                mismatches.append(
                    f"Listing {i+1} (ID: {listing.listing_id}): City mismatch. Expected '{filters['City']}', got '{listing.city}'.")

            if listing.transmission and filters["Transmission"].lower() not in listing.transmission.lower():
                mismatches.append(
                    f"Listing {i+1} (ID: {listing.listing_id}): Transmission mismatch. Expected '{filters['Transmission']}', got '{listing.engine_type}'.")

        if mismatches:
            self.fail(
                "Found listings that do not match the applied filters:\\n" + "\\n".join(mismatches))
        else:
            print("All fetched listings successfully match the applied filters.")
    # --------------------------------------------------------------
    # Remarks: Poorly Implemented Keyword Based Searching Logic, Includes
    # non matching results in the search results.
    # Always Fails
    # --------------------------------------------------------------

    # --------------------------------------------------------------
    # Test Case 2: Test the prebuilt filter functionality
    # --------------------------------------------------------------

    def test_apply_city_filter(self):
        """Tests applying the 'City' filter for 'Lahore'."""
        print("\nRunning test: test_apply_city_filter_lahore")
        filter_name = "City"
        option_value = "Lahore"

        success = self.filter_interactor.verify_url_change(
            self.filter_interactor.select_filter_option,
            filter_name,
            option_value
        )

        self.assertTrue(
            success, f"URL did not change after attempting to select filter '{option_value}' in '{filter_name}'.")
        self.assertIn("lahore", self.driver.current_url.lower(
        ), "'lahore' not found in the final URL after applying the filter.")

    def test_apply_color_filter(self):
        """Tests applying the 'Color' filter for 'Beige'."""
        print("\nRunning test: test_apply_color_filter")
        filter_name = "Color"
        option_value = "Beige"

        success = self.filter_interactor.verify_url_change(
            self.filter_interactor.select_filter_option,
            filter_name,
            option_value
        )

        self.assertTrue(
            success, f"URL did not change after attempting to select filter '{option_value}' in '{filter_name}'.")

    def test_apply_make_filter(self):
        """Tests applying the 'Make' filter for 'Mercedes Benz'."""
        print("\nRunning test: test_apply_Make_filter")
        self.navigator.go_to_search_page()
        filter_name = "Make"
        option_value = "Mercedes Benz"

        success = self.filter_interactor.verify_url_change(
            self.filter_interactor.select_filter_option,
            filter_name,
            option_value
        )

        self.assertTrue(
            success, f"URL did not change after attempting to select filter '{option_value}' in '{filter_name}'.")

    def test_verify_listings_match_filters(self):
        """
        Applies City and Price filters, then verifies listings match.
        """
        print("\\nRunning test: test_verify_listings_match_filters")

        target_city = "Gujranwala"
        min_price = 10000000  # 1 crore
        max_price = 2500000  # 25 lacs

        
        print(f"Applying filter: City = {target_city}")
        city_success = self.filter_interactor.verify_url_change(
            self.filter_interactor.select_filter_option,
            "City",
            target_city
        )
        self.assertTrue(
            city_success, f"URL did not change after applying City filter '{target_city}'.")

        time.sleep(3)
        print(f"Applying filter: Price Range = {min_price} to {max_price}")
        self.filter_interactor.apply_range_filter(
            "Price Range", min_value=min_price, max_value=max_price)
        time.sleep(3)

        if max_price < min_price:
            min_price, max_price = max_price, min_price

        print("Fetching listing data after applying filters...")
        listings = self.filter_interactor.get_current_listings_data()

        self.assertGreater(len(
            listings), 0, "No listings found after applying filters. Check filter criteria or website state.")

        print(f"Verifying {len(listings)} listings against filters...")
        mismatches = []

        for i, listing in enumerate(listings):
            # Verify City
            if listing.city and target_city.lower() not in listing.city.lower():
                mismatches.append(
                    f"Listing {i+1} (ID: {listing.listing_id}): City mismatch. Expected '{target_city}', got '{listing.city}'.")

            # Verify Price
            if listing.price is not None:
                if isinstance(listing.price, int):
                    if not (min_price <= listing.price <= max_price):
                        mismatches.append(
                            f"Listing {i+1} (ID: {listing.listing_id}): Price mismatch. Price {listing.price} not in range [{min_price}-{max_price}].")
                else:
                    mismatches.append(
                        f"Listing {i+1} (ID: {listing.listing_id}): Price could not be parsed to integer ('{listing.price}'). Cannot verify range.")
            else:
                mismatches.append(
                    f"Listing {i+1} (ID: {listing.listing_id}): Price is missing. Cannot verify range.")

        if mismatches:
            self.fail(
                "Found listings that do not match the applied filters:\\n" + "\\n".join(mismatches))
        else:
            print("All fetched listings successfully match the applied filters.")

    def test_verify_listings_match_filters_v2(self):
        """
        Applies City and Price filters, then verifies listings match.
        """
        print("\\nRunning test: test_verify_listings_match_filters")

        target_city = "Gujranwala"
        transmission = "Automatic"
        engine_type = "Petrol"
        picture_availability = "With Pictures"

        # --- Apply City Filter ---
        print(f"Applying filter: City = {target_city}")
        city_success = self.filter_interactor.verify_url_change(
            self.filter_interactor.select_filter_option,
            "City",
            target_city
        )
        self.assertTrue(
            city_success, f"URL did not change after applying City filter '{target_city}'.")

        self.filter_interactor.sleep_driver(3)

        print(f"Applying filter: City = {transmission}")
        city_success = self.filter_interactor.verify_url_change(
            self.filter_interactor.select_filter_option,
            "Transmission",
            transmission
        )
        self.assertTrue(
            city_success, f"URL did not change after applying Transmission filter '{transmission}'.")

        self.filter_interactor.sleep_driver(3)

        print(f"Applying filter: City = {engine_type}")
        city_success = self.filter_interactor.verify_url_change(
            self.filter_interactor.select_filter_option,
            "Engine Type",
            engine_type
        )
        self.assertTrue(
            city_success, f"URL did not change after applying Engine Type filter '{engine_type}'.")

        self.filter_interactor.sleep_driver(3)

        print(f"Applying filter: City = {picture_availability}")
        city_success = self.filter_interactor.verify_url_change(
            self.filter_interactor.select_filter_option,
            "Picture Availability",
            picture_availability
        )
        self.assertTrue(
            city_success, f"URL did not change after applying Picture Availability filter '{picture_availability}'.")

        time.sleep(3)

        # --- Fetch Listing Data ---
        print("Fetching listing data after applying filters...")
        listings = self.filter_interactor.get_current_listings_data()

        self.assertGreater(len(
            listings), 0, "No listings found after applying filters. Check filter criteria or website state.")

        print(f"Verifying {len(listings)} listings against filters...")
        mismatches = []

        for i, listing in enumerate(listings):
            # Verify City
            if listing.city and target_city.lower() not in listing.city.lower():
                mismatches.append(
                    f"Listing {i+1} (ID: {listing.listing_id}): City mismatch. Expected '{target_city}', got '{listing.city}'.")

            # Verify Transmission
            if listing.transmission and transmission.lower() not in listing.transmission.lower():
                mismatches.append(
                    f"Listing {i+1} (ID: {listing.listing_id}): Transmission mismatch. Expected '{transmission}', got '{listing.transmission}'.")

            # Verify Engine Type
            if listing.engine_type and engine_type.lower() not in listing.engine_type.lower():
                mismatches.append(
                    f"Listing {i+1} (ID: {listing.listing_id}): Engine Type mismatch. Expected '{engine_type}', got '{listing.engine_type}'.")

            # Verify Picture Availability boolean
            if picture_availability == "With Pictures" and not listing.picture_availability:
                mismatches.append(
                    f"Listing {i+1} (ID: {listing.listing_id}): Picture Availability mismatch. Expected '{picture_availability}', got '{listing.picture_availability}'.")

        if mismatches:
            self.fail(
                "Found listings that do not match the applied filters:\\n" + "\\n".join(mismatches))
        else:
            print("All fetched listings successfully match the applied filters.")
    # --------------------------------------------------------------
    # Remarks: N/A
    # --------------------------------------------------------------

    # --------------------------------------------------------------
    # Test Case 3: Test the Filters across multiple webpages
    # Test Case 4: Multi page filter listing results verification
    # --------------------------------------------------------------
    def test_verify_imported_assembly_across_pages(self):
        """
        Applies 'Assembly: Imported' filter and verifies listings on first 3 pages.
        """
        print("\\nRunning test: test_verify_imported_assembly_across_pages")

        # --- Filter Criteria ---
        filter_name = "Assembly"
        option_value = "Imported"
        max_pages_to_check = 3

        # --- Apply Filter ---
        print(f"Applying filter: {filter_name} = {option_value}")
        self.filter_interactor.select_filter_option(filter_name, option_value)
        time.sleep(3)
        print("Filter applied. Proceeding to check listings.")

        # --- Initialization ---
        mismatches = []
        original_window_handle = self.driver.current_window_handle
        current_page = 1

        # --- Page Traversal Loop ---
        while current_page <= max_pages_to_check:
            print(f"--- Checking Page {current_page} ---")

            # Get listings on the current page
            listings_on_page = self.filter_interactor.get_current_listings_data()

            if not listings_on_page:
                print(
                    f"No listings found on page {current_page}. Stopping check.")
                break
            counter = 0
            print(
                f"Found {len(listings_on_page)} listings on page {current_page}. Verifying assembly...")
            # --- Listing Verification Loop ---
            for i, listing_summary in enumerate(listings_on_page):
                if not listing_summary.url:
                    print(
                        f"Warning: Listing {i+1} (ID: {listing_summary.listing_id}) on page {current_page} has no URL. Skipping.")
                    continue
                if counter >= 5:
                    print(
                        f"  Warning: Skipping listing {i+1} (ID: {listing_summary.listing_id}) due to too many open tabs.")
                    break
                counter += 1
                print(
                    f"  Checking listing {i+1} (ID: {listing_summary.listing_id})...")
                new_tab_handle = None
                try:
                    new_tab_handle = self.navigator.open_listing_page_new_tab(
                        listing_summary.url)
                    if not new_tab_handle:
                        print(
                            f"  Error: Failed to open or switch to new tab for listing {listing_summary.listing_id}. Skipping.")
                        continue

                    time.sleep(2)
                    try:
                        self.wait.until(EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "table.table-engine-detail, .price-box")))
                    except TimeoutException:
                        print(
                            f"  Warning: Timed out waiting for detail page elements for listing {listing_summary.listing_id}.")

                    self.filter_interactor.sleep_driver(1)
                    listing_details = self.extractor.extract_listing_page_data(
                        self.driver)

                    # Verify Assembly
                    if listing_details.assembly is None:
                        print(f"Assembly Unavailable for the listing: {listing_summary.listing_id}")
                    elif option_value.lower() not in listing_details.assembly.lower():
                        mismatches.append(
                            f"Page {current_page}, Listing {i+1} (ID: {listing_summary.listing_id}, URL: {listing_summary.url}): Assembly mismatch. Expected '{option_value}', got '{listing_details.assembly}'.")
                    else:
                        print(
                            f"    Assembly '{listing_details.assembly}' matches expected '{option_value}'. OK.")

                except Exception as e:
                    print(
                        f"  Error processing listing {listing_summary.listing_id} on page {current_page}: {e}")
                    mismatches.append(
                        f"Page {current_page}, Listing {i+1} (ID: {listing_summary.listing_id}, URL: {listing_summary.url}): Unexpected error during processing: {e}")
                finally:
                    if new_tab_handle:
                        self.navigator.close_current_tab_and_switch_back(
                            original_window_handle)

            # --- Go to Next Page ---
            if current_page < max_pages_to_check:
                print(f"Attempting to navigate to page {current_page + 1}...")
                if not self.navigator.go_to_next_page():
                    print(
                        f"Could not navigate to next page (already on last page or error). Stopping check.")
                    break

            current_page += 1

        # --- Assert Results ---
        self.assertFalse(mismatches,
                         f"Found listings that do not match the '{option_value}' assembly filter or had errors:\\n" + "\\n".join(mismatches))

        print(
            f"Successfully verified assembly for all checked listings across {current_page-1} page(s).")

    # --------------------------------------------------------------
    # Test Case 5: Test the Filters across multiple webpages
    # - --------------------------------------------------------------

    def test_sorting_by_price(self):
        """Tests sorting by price (High→Low) across the first 3 pages using summary data only."""
        print("\nRunning test: test_sorting_by_price_quick")

        # Apply the sort
        print("Applying sort: Price: High to Low")
        self.filter_interactor.apply_sort("Price: High to Low")
        time.sleep(3)

        mismatches = []
        current_page = 1

        # Loop over pages
        while current_page <= 3:
            print(f"--- Page {current_page} ---")
            listings = self.filter_interactor.get_current_listings_data()
            if not listings:
                print(f"No listings found on page {current_page}, stopping.")
                break

            # Extract and validate prices
            prices = []
            for idx, summary in enumerate(listings, start=1):
                price = summary.price
                if price is None:
                    mismatches.append(
                        f"Page {current_page} Listing {idx}: missing price."
                    )
                elif not isinstance(price, int):
                    mismatches.append(
                        f"Page {current_page} Listing {idx}: price '{price}' not an int."
                    )
                else:
                    prices.append(price)

            # Check the prices list is sorted descending
            if prices and prices != sorted(prices, reverse=True):
                mismatches.append(
                    f"Page {current_page}: prices not in descending order: {prices}"
                )
            else:
                print(f"  Prices on page {current_page} are correctly sorted.")

            # Advance to next page (if possible)
            try:
                self.navigator.go_to_next_page()
                time.sleep(3)
                current_page += 1
            except TimeoutException:
                print("No further pages available; ending at page", current_page)
                break

        # 6. Assert no mismatches were found
        if mismatches:
            self.fail("Sorting mismatches:\n" + "\n".join(mismatches))
        else:
            print("✅ All pages verified: listings are sorted High→Low by price.")

if __name__ == '__main__':
    unittest.main()
