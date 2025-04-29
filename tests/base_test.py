import unittest
from core.navigator import PakWheelsNavigator
import os
import logging
import traceback

class BaseTest(unittest.TestCase):
    """Base class for tests needing a WebDriver instance."""
    LOG_PATH = os.path.join(os.getcwd(), "tests.log")

    @classmethod
    def setUpClass(cls):
        cls.navigator = PakWheelsNavigator()
        cls.driver, cls.wait = cls.navigator.initialize_driver()

        logger = logging.getLogger("pakwheels_tests")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            fh = logging.FileHandler(cls.LOG_PATH, mode="a", encoding="utf-8")
            fh.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)-8s %(message)s",
                "%Y-%m-%d %H:%M:%S"
            ))
            logger.addHandler(fh)

        cls.logger = logger

    @classmethod
    def tearDownClass(cls):
        """Tear down the WebDriver after all tests in the class."""
        if cls.navigator:
            cls.navigator.close_driver()

    def setUp(self):
        """Optional: Actions before each test method (e.g., navigate to base URL)."""
        pass
    
    def tearDown(self):
        outcome = self._outcome
        if hasattr(outcome, 'errors'):
            result = self.defaultTestResult()
            self._feedErrorsToResult(result, outcome.errors)
        else:
            result = outcome.result

        combined = result.errors + result.failures

        for test_case, exc_info in combined:
            if test_case is self:
                if isinstance(exc_info, tuple) and len(exc_info) == 3:
                    tb = "".join(traceback.format_exception(*exc_info))
                else:
                    tb = str(exc_info)
                self.logger.error(f"FAIL: {self.id()}\n{tb}")
                break
        else:
            self.logger.info(f"PASS: {self.id()}")
