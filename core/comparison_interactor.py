from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from core.navigator import PakWheelsNavigator
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import time


class ComparisonInteractor:
    MODAL_XPATH = "//div[contains(@class,'cat-selection') or contains(@class,'comparison-modal')]"

    def __init__(self, driver, wait, navigator: PakWheelsNavigator):
        self.driver = driver
        self.wait = wait
        self.navigator = navigator
        
    def do_comparison(self, car_details: list[dict[str:str]]) -> bool:
        if not self.navigator.is_on_comparison_page():
            print("  ✖ Not on comparison page")
            self.navigator.go_to_comparison_page()
            
        if not len(car_details) >= 1 and len(car_details) <= 3:
            print("  ✖ Invalid number of cars to compare")
            return False
        
        print("  Starting comparison process…")
        for i, details in enumerate(car_details):
            print(f"  Selecting car {i+1}…")
            if not self.select_car(i, details):
                print(f"  ✖ Failed to select car {i+1}")
                return False
        print("  All cars selected successfully.")
        
        success = self.click_compare()
        
        if success:
            print("  ✓ Comparison initiated successfully.")
            return True
        else:
            print("  ✖ Failed to initiate comparison.")
            return False
    
    

    def select_car(self, slot_num: int, details: dict) -> bool:
        slot = self.wait.until(EC.element_to_be_clickable(
            (By.ID, f"vehicle_selector_{slot_num}")
        ))

        self._dismiss_overlay_link()
        self.navigator._close_google_signin_popup(timeout=2)
        time.sleep(0.5)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", slot)
        time.sleep(0.2)
        self.driver.execute_script("arguments[0].click();", slot)
        print(f"  → force‑clicked slot {slot} via JS")

        if not self._click_with_actions(slot):
            self.driver.execute_script("arguments[0].click();", slot)

        print(f"  Opened modal for slot {slot_num}")

        self._close_interfering_popup()
        time.sleep(0.5)

        if not self._select_make(details["Make"]):
            return False

        if not self._select_model(details["Model"]):
            return False

        self.navigator._close_google_signin_popup(timeout=2)

        self._close_interfering_popup()
        version = details.get("Version")
        if version and not self._select_version(version):
            return False

        print(f"  ✓ Car {slot_num} selected: {details}")
        return True

    def _click_with_actions(self, elem):
        """
        As a last resort, move to the element and click with ActionChains.
        """
        try:
            actions = ActionChains(self.driver)
            actions.move_to_element(elem).click().perform()
            print("  ✔ Clicked via ActionChains")
            return True
        except Exception as e:
            print(f"  ✖ ActionChains click failed: {e}")
            return False

    def _select_make(self, make_text):
        print(f"    Picking Make: {make_text}")
        try:
            make_elements = self.wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, "//li[contains(@class, 'make')]//a")))
            print(f"      Found {len(make_elements)} make elements")

            for elem in make_elements:
                if elem.text.strip().lower() == make_text.strip().lower():
                    try:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", elem)
                        time.sleep(0.5)
                        elem.click()
                        time.sleep(1)
                        print(f"      → clicked {make_text}")
                        return True
                    except Exception as e:
                        print(f"      ✖ click failed: {e}")
                        try:
                            self.driver.execute_script(
                                "arguments[0].click();", elem)
                            time.sleep(1)
                            print(f"      → clicked {make_text} via JS")
                            return True
                        except Exception as js_e:
                            print(f"      ✖ JS click failed: {js_e}")
            print(f"      ✖ Make '{make_text}' not found or not clickable")
            return False
        except Exception as e:
            print(f"      ✖ Error locating make elements: {e}")
            return False

    def _select_model(self, model_text: str) -> bool:
        print(f"    Picking Model: {model_text}")
        try:
            self._dismiss_overlay_link()

            self.wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "ul.model-listings.show li.model a"
            )))
            time.sleep(0.2)

            links = self.driver.find_elements(
                By.CSS_SELECTOR,
                "ul.model-listings.show li.model a"
            )
            available = [l.text.strip() for l in links]
            print("      Available models:", available)

            for link in links:
                if link.text.strip().lower() == model_text.strip().lower():
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", link
                    )
                    time.sleep(0.2)
                    try:
                        link.click()
                    except Exception:
                        self.driver.execute_script(
                            "arguments[0].click();", link)
                    time.sleep(1)
                    print(f"      → clicked {model_text}")
                    return True

            print(f"      ✖ Model '{model_text}' not found")
            return False

        except Exception as e:
            print(f"      ✖ could not pick Model '{model_text}': {e}")
            return False

    def _select_version(self, version_text):
        print(f"    Picking Version: {version_text}")
        self._close_interfering_popup(timeout=2)
        try:
            xpath = f"//li[contains(@class,'version')]//a[contains(text(),'{version_text}')]"
            elem = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, xpath)))
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", elem)
            time.sleep(0.5)
            elem.click()
            time.sleep(1)
            print(f"      → clicked {version_text}")
            return True
        except Exception as e:
            print(f"      ✖ could not click Version '{version_text}': {e}")
            return False

    def _close_interfering_popup(self, timeout=5):
        """
        Closes the Download‑App or Google‑Sign‑In modal if present.
        """
        try:
            modal = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((
                    By.XPATH,
                    "//div[@id='download_apps' or @id='googleSignInModal']"
                ))
            )
            close_btn = modal.find_element(
                By.CSS_SELECTOR, ".close, .btn-close, .dismiss-btn")
            close_btn.click()
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located((
                    By.XPATH,
                    "//div[@id='download_apps' or @id='googleSignInModal']"
                ))
            )
            print("  ✔ Overlay closed")
        except Exception:
            pass
    '''
    
    '''

    def _dismiss_overlay_link(self, timeout=2):
        """
        Wait briefly for any full‑page <a href="#"> overlay, then remove it via JS.
        """
        try:
            overlay = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a[href='#'].overlay, a[href='#'].full-field-overlay"))
            )
            self.driver.execute_script("arguments[0].remove();", overlay)
            print("  ✔ Removed stray overlay <a href='#'>")
        except Exception:
            pass

    def click_compare(self) -> bool:
        """
        Clicks the Compare button on the compare page.
        """
        print("Attempting to click the Compare button…")
        try:
            xpath = (
                "//*[@id='main-container']//form"
                "//input[@type='submit' and translate(@value,'COMPARE','compare')='compare']"
            )

            btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, xpath)))
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.5)
            btn.click()
            print("Compare button clicked.")
            return True
        except Exception as e:
            print(f"Error clicking Compare button: {e}")
            return False
