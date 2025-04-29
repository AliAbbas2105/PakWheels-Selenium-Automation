import unittest
from core.models import *
from tests.base_test import BaseTest
from core.search_interactor import FilterInteractor
from core.comparison_interactor import ComparisonInteractor
from core.extractor import ListingExtractor
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import time
from typing import List, Dict, Any, Callable, Tuple


class ComparisonTest(BaseTest):

    def setUp(self):
        """Navigate to the search page before each test."""
        self.comparison_interactor = ComparisonInteractor(
            self.driver, self.wait, self.navigator)
        self.extractor = ListingExtractor()

    # --------------------------------------------------------------
    # Test Case 6: Test the Comaprison of Vehicles
    # --------------------------------------------------------------

    def test_select_two_cars(self):
        """Tests selecting two cars for comparison."""
        print("\nRunning test: test_select_two_cars")

        try:
            self.driver.save_screenshot("start_page.png")
            print("Starting page screenshot saved")

            self.navigator.go_to_comparison_page()
            time.sleep(3)

            self.driver.save_screenshot("comparison_page.png")
            print("Comparison page screenshot saved")

            print("\nPage title:", self.driver.title)
            print("Current URL:", self.driver.current_url)

            car_two_details = {
                "Make": "Toyota",
                "Model": "Corolla",
                "Version": "XLi"
            }
            car_one_details = {
                "Make": "Honda",
                "Model": "Vezel",
                "Version": "G"
            }

            print("\nAttempting to select first car:", car_one_details)
            success = self.comparison_interactor.select_car(0, car_one_details)

            if not success:
                print("WARNING: Failed to select first car, but continuing test")
                self.driver.save_screenshot("first_car_failure.png")

            print("\nAttempting to select second car:", car_two_details)
            success_2 = self.comparison_interactor.select_car(
                1, car_two_details)
            
            if not success_2:
                print("WARNING: Failed to select second car")
                self.driver.save_screenshot("second_car_failure.png")

            if success or success_2:
                print("\nAttempting to click compare button")
                self.comparison_interactor.click_compare()
                time.sleep(3)
                self.driver.save_screenshot("after_compare.png")

            self.assertTrue(success, "Failed to select the first car.")
            self.assertTrue(success_2, "Failed to select the second car.")

            current_url = self.driver.current_url
            self.assertIn(car_one_details["Make"].lower(), current_url.lower(
            ), "Comparison page not displayed after selecting cars.")
            self.assertIn(car_two_details["Make"].lower(), current_url.lower(
            ), "Comparison page not displayed after selecting cars.")
            print("Successfully selected two cars for comparison.")

        except Exception as e:
            print(f"Unexpected error in test: {e}")
            self.driver.save_screenshot("unexpected_error.png")
            raise

    def test_select_three_cars(self):
        self.navigator.go_to_comparison_page()

        print("\nPage title:", self.driver.title)
        print("Current URL:", self.driver.current_url)

        car_one_details = {
            "Make": "Bugatti",
            "Model": "Chiron",
            "Version": "Sport"
        }
        car_two_details = {
            "Make": "Ford",
            "Model": "Escort",
            "Version": "2.0"
        }
        car_three_details = {
            "Make": "McLaren",
            "Model": "Artura",
            "Version": "Standard"
        }

        print("\nAttempting to select first car:", car_one_details)
        success = self.comparison_interactor.select_car(0, car_one_details)

        print("\nAttempting to select second car:", car_two_details)
        success_2 = self.comparison_interactor.select_car(1, car_two_details)

        print("\nAttempting to select third car:", car_three_details)
        success_3 = self.comparison_interactor.select_car(2, car_three_details)

        if success and success_2 and success_3:
            print("\nAttempting to click compare button")
            self.comparison_interactor.click_compare()
            time.sleep(3)
            self.driver.save_screenshot("after_compare.png")

        self.assertTrue(success, "Failed to select the first car.")
        self.assertTrue(success_2, "Failed to select the second car.")
        self.assertTrue(success_3, "Failed to select the third car.")

        self.assertIn(car_one_details["Make"].lower(), self.driver.current_url.lower(
        ), "Comparison page not displayed after selecting cars.")
        self.assertIn(car_two_details["Make"].lower(), self.driver.current_url.lower(
        ), "Comparison page not displayed after selecting cars.")
        self.assertIn(car_three_details["Make"].lower(), self.driver.current_url.lower(
        ), "Comparison page not displayed after selecting cars.")
        print("Successfully selected three cars for comparison.")

    def test_compared_data(self):
        """
        Tests selecting cars, comparing them, extracting data, 
        and validating the results based on existence, difference, and basic intelligibility.
        """
        print("\nRunning test: test_compared_data")

        self.navigator.go_to_comparison_page()
        time.sleep(2)

        cars_to_compare = [
            {
                "Make": "Bugatti",
                "Model": "Chiron",
                "Version": "Sport"
            },
            {
                "Make": "Rolls Royce",
                "Model": "Wraith",
                "Version": "Black Badge"
            },
            {
                "Make": "McLaren",
                "Model": "Artura",
                "Version": "Standard"
            }
        ]

        compare_success = self.comparison_interactor.do_comparison(
            cars_to_compare)
        self.assertTrue(compare_success,
                        "Failed to select cars for comparison.")

        print("Waiting for comparison results page to load...")
        try:
            self.wait.until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "table.vehicle-compare-head")))
            self.wait.until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "div.specs-wrapper.spec-compare-details")))
            print("Comparison results page loaded.")
        except Exception as e:
            self.fail(f"Comparison results page did not load correctly: {e}")

        time.sleep(1)

        cars_compared_count = len(cars_to_compare)
        result: ComparisonResult = self.extractor.extract_comparison_data(
            self.driver)

        #print("Extracted comparison data:", result) #Enable to print the extracted data

        print("Validating extracted comparison data...")
        self.assertIsInstance(
            result, ComparisonResult, "Extractor did not return a ComparisonResult object.")

        self.assertTrue(any(name is not None for name in result.car_names[:cars_compared_count]),
                        "Car names were not extracted from the header.")

        if cars_compared_count > 1:
            self.assertTrue(any(price is not None for price in result.prices[:cars_compared_count]),
                            "Car prices were not extracted from the header for any compared car.")
        self.assertEqual(len(result.ratings), 3,
                         "Ratings list length is incorrect.")
        self.assertEqual(len(result.review_counts), 3,
                         "Review counts list length is incorrect.")

        self.assertGreater(len(result.sections), 0,
                           "No comparison sections were extracted.")

        found_difference = False
        total_specs_checked = 0
        unintelligible_features = []
        all_identical_features = []

        for section in result.sections:
            self.assertTrue(section.title, f"Section found with no title.")

            for spec in section.specifications:
                total_specs_checked += 1
                self.assertTrue(
                    spec.feature, f"Specification found with no feature name in section '{section.title}'.")

                self.assertEqual(len(spec.values), cars_compared_count,
                                 f"Feature '{spec.feature}' in section '{section.title}' has incorrect number of values. Expected {cars_compared_count}, got {len(spec.values)}. Values: {spec.values}")

                valid_values = [
                    v for v in spec.values if v is not None and v != '']
                if not valid_values and True not in spec.values and False not in spec.values:
                    unintelligible_features.append(
                        f"'{spec.feature}' in section '{section.title}' (All values None/Empty: {spec.values})")
                    continue

                unique_values = set(
                    v for v in spec.values if v is not None and v != '')
                if len(unique_values) > 1:
                    found_difference = True
                    # print(f"  Difference found for '{spec.feature}': {spec.values}") # Optional: print differences
                elif len(unique_values) == 1:
                    all_identical_features.append(
                        f"'{spec.feature}' in section '{section.title}' (Value: {list(unique_values)[0]})")

        self.assertGreater(
            total_specs_checked, 5, f"Very few specifications ({total_specs_checked}) were extracted and checked across all sections.")

        self.assertFalse(unintelligible_features,
                         f"Found features with potentially unintelligible (all None/Empty) values:\n - " + "\n - ".join(unintelligible_features))

        self.assertTrue(found_difference,
                        f"Comparison failed: All extracted specification values were identical across the compared cars for all features checked ({len(all_identical_features)} features).")

        print("Comparison data validation successful.")
