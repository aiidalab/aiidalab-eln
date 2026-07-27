from pathlib import Path
from urllib.parse import urljoin

import pytest
import selenium.webdriver.support.expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait


@pytest.fixture(scope="function")
def selenium_driver(selenium, notebook_service):
    def _selenium_driver(nb_path):
        url, token = notebook_service
        url_with_token = urljoin(
            url, f"apps/apps/aiidalab-eln/{nb_path}?token={token}"
        )
        selenium.get(f"{url_with_token}")
        # By default, let's allow selenium functions to retry for 60s
        # till a given element is loaded, see:
        # https://selenium-python.readthedocs.io/waits.html#implicit-waits
        selenium.implicitly_wait(60)
        window_width = 800
        window_height = 600
        selenium.set_window_size(window_width, window_height)

        selenium.find_element(By.ID, "ipython-main-app")
        selenium.find_element(By.ID, "notebook-container")
        selenium.find_element(By.ID, "appmode-busy")
        # We wait until the appmode spinner disappears. However,
        # this does not seem to be fully robust, as the spinner might flash
        # while the page is still loading. So we add explicit sleep here as well.
        WebDriverWait(selenium, 240).until(
            ec.invisibility_of_element((By.ID, "appmode-busy"))
        )

        return selenium

    return _selenium_driver


@pytest.fixture
def final_screenshot(request, screenshot_dir, selenium):
    """Take screenshot at the end of the test.
    Screenshot name is generated from the test function name
    by stripping the 'test_' prefix
    """
    screenshot_name = f"{request.function.__name__[5:]}.png"
    screenshot_path = Path.joinpath(screenshot_dir, screenshot_name)
    yield
    selenium.get_screenshot_as_file(screenshot_path)
