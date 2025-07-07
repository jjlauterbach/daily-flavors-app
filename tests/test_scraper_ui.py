import unittest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

class TestScraperUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        cls.driver = webdriver.Chrome(options=options)
        cls.driver.set_window_size(1200, 900)
        # Change this URL if your app runs on a different port or path
        cls.url = 'http://localhost:8080/'

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_flavor_cards_present(self):
        self.driver.get(self.url)
        # Wait for JS to load flavors (increase if your backend is slow)
        time.sleep(5)
        cards = self.driver.find_elements(By.CLASS_NAME, 'flavor-card')
        self.assertGreater(len(cards), 0, 'No flavor cards found on the page')
        for card in cards:
            name = card.find_element(By.CLASS_NAME, 'flavor-name').text
            self.assertTrue(name and len(name) > 1, 'Flavor name missing or too short')
            date = card.find_element(By.CLASS_NAME, 'flavor-date').text
            self.assertTrue(date, 'Flavor date missing')
            desc = card.find_element(By.CLASS_NAME, 'flavor-description').text
            self.assertTrue(desc is not None, 'Flavor description missing')

if __name__ == '__main__':
    unittest.main()
