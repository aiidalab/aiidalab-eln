import time

from selenium.webdriver.common.by import By


def test_eln_configure(selenium_driver, final_screenshot):
    driver = selenium_driver("eln_configure.ipynb")
    driver.find_element(By.XPATH, '//button[text()="Set as default"]')

def test_eln_import(selenium_driver, final_screenshot):
    driver = selenium_driver("eln_import.ipynb")
    # TODO: This find_element is not specific enough it seems,
    # on the screenshot the page is still loading.
    driver.find_element(By.ID, "tooltip")
    time.sleep(5)