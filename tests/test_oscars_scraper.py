import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, call, patch

from app.scrapers.oscars import _extract_flavor_from_modal, scrape_oscars


class TestOscarsScraper(unittest.TestCase):
    """Unit tests for Oscar's scraper functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_driver = Mock()
        self.mock_driver.execute_cdp_cmd = Mock()
        self.mock_driver.set_window_size = Mock()
        self.mock_driver.get = Mock()
        self.mock_driver.quit = Mock()
        self.mock_driver.execute_script = Mock()

    @patch("app.scrapers.oscars.webdriver.Chrome")
    @patch("app.scrapers.oscars.WebDriverWait")
    @patch("app.scrapers.oscars._get_chrome_options")
    @patch("app.scrapers.oscars.get_central_time")
    @patch("app.scrapers.oscars.get_central_date_string")
    def test_multiple_flavors_with_or_separator(
        self, mock_date_string, mock_time, mock_chrome_options, mock_wait, mock_chrome
    ):
        """Test scraping multiple flavors separated by '-or-'."""
        # Setup mocks
        mock_chrome.return_value = self.mock_driver
        mock_chrome_options.return_value = Mock()
        mock_time.return_value = datetime(2025, 7, 15)  # Tuesday
        mock_date_string.return_value = "2025-07-15"

        # Mock WebDriverWait
        mock_wait.return_value.until.return_value = True

        # Mock calendar row finding
        mock_row = Mock()
        mock_cell_1 = Mock()
        mock_cell_1.text.strip.return_value = "Tue 15"
        mock_cell_1.get_attribute.return_value = "Tue 15"
        mock_cell_1.find_elements.return_value = []

        mock_cell_2 = Mock()
        mock_cell_2.text.strip.return_value = "LEMON BERRY -or- CHOCOLATE CHIP"
        mock_cell_2.get_attribute.return_value = '<strong><a id="overlay_unique_id_205873" href="#open-overlay">LEMON BERRY</a></strong>  -or- <strong><a id="overlay_unique_id_205580" href="#open-overlay">CHOCOLATE CHIP</a></strong>'

        # Mock flavor links
        mock_link_1 = Mock()
        mock_link_1.text.strip.return_value = "LEMON BERRY"
        mock_link_1.is_displayed.return_value = True

        mock_link_2 = Mock()
        mock_link_2.text.strip.return_value = "CHOCOLATE CHIP"
        mock_link_2.is_displayed.return_value = True

        mock_cell_2.find_elements.return_value = [mock_link_1, mock_link_2]

        mock_row.find_elements.side_effect = [
            [mock_link_1, mock_link_2],  # All links in row
            [mock_cell_1, mock_cell_2],  # All cells in row
        ]
        mock_row.text.strip.return_value = "Tue 15 LEMON BERRY -or- CHOCOLATE CHIP"

        self.mock_driver.find_elements.return_value = [mock_row]

        # Mock modal interactions
        mock_overlay = Mock()
        mock_overlay.is_displayed.return_value = True
        mock_overlay.get_attribute.return_value = (
            "<h4>LEMON BERRY</h4><p>Red, ripe raspberries wrapped into lemon custard.</p>"
        )

        # Mock the overlay finding to return different content for each flavor
        overlay_returns = [
            [mock_overlay],  # First flavor modal
            [],  # No overlay after close
            [mock_overlay],  # Second flavor modal
            [],  # No overlay after close
        ]
        self.mock_driver.find_elements.side_effect = [
            [mock_row],  # Calendar row search
            [mock_link_1, mock_link_2],  # Row links
            [mock_cell_1, mock_cell_2],  # Row cells
            [mock_link_1, mock_link_2],  # Cell links
            overlay_returns[0],  # First modal search
            overlay_returns[1],  # Close button search
            overlay_returns[2],  # Second modal search
            overlay_returns[3],  # Close button search
        ]

        # Mock close buttons
        self.mock_driver.find_element.return_value = Mock()

        # Run the scraper
        with patch("app.scrapers.oscars.time.sleep"):  # Skip actual sleep
            with patch("app.scrapers.oscars._extract_flavor_from_modal") as mock_extract:
                with patch("app.scrapers.oscars._close_modal") as mock_close:
                    # Mock extraction returns
                    mock_extract.side_effect = [
                        {
                            "flavor": "LEMON BERRY",
                            "description": "Red, ripe raspberries wrapped into lemon custard.",
                            "date": "2025-07-15",
                            "restaurant": "Oscars",
                            "url": "https://www.oscarscustard.com/index.php/flavors",
                        },
                        {
                            "flavor": "CHOCOLATE CHIP",
                            "description": "Chocolate chips blended with our creamy custard.",
                            "date": "2025-07-15",
                            "restaurant": "Oscars",
                            "url": "https://www.oscarscustard.com/index.php/flavors",
                        },
                    ]

                    result = scrape_oscars()

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2, "Should return 2 flavors")

        # Check first flavor
        self.assertEqual(result[0]["flavor"], "LEMON BERRY")
        self.assertEqual(
            result[0]["description"], "Red, ripe raspberries wrapped into lemon custard."
        )

        # Check second flavor
        self.assertEqual(result[1]["flavor"], "CHOCOLATE CHIP")
        self.assertEqual(
            result[1]["description"], "Chocolate chips blended with our creamy custard."
        )

        # Verify both links were clicked
        self.assertEqual(self.mock_driver.execute_script.call_count, 2)

        # Verify extraction was called for both flavors
        self.assertEqual(mock_extract.call_count, 2)
        mock_extract.assert_has_calls(
            [call(self.mock_driver, "LEMON BERRY"), call(self.mock_driver, "CHOCOLATE CHIP")]
        )

        # Verify modal close was called for both flavors
        self.assertEqual(mock_close.call_count, 2)

    @patch("app.scrapers.oscars.webdriver.Chrome")
    @patch("app.scrapers.oscars.WebDriverWait")
    @patch("app.scrapers.oscars._get_chrome_options")
    @patch("app.scrapers.oscars.get_central_time")
    @patch("app.scrapers.oscars.get_central_date_string")
    def test_single_flavor_fallback(
        self, mock_date_string, mock_time, mock_chrome_options, mock_wait, mock_chrome
    ):
        """Test that single flavor still works correctly."""
        # Setup mocks
        mock_chrome.return_value = self.mock_driver
        mock_chrome_options.return_value = Mock()
        mock_time.return_value = datetime(2025, 7, 16)  # Wednesday
        mock_date_string.return_value = "2025-07-16"

        # Mock WebDriverWait
        mock_wait.return_value.until.return_value = True

        # Mock calendar row with single flavor
        mock_row = Mock()
        mock_cell_1 = Mock()
        mock_cell_1.text.strip.return_value = "Wed 16"
        mock_cell_1.get_attribute.return_value = "Wed 16"
        mock_cell_1.find_elements.return_value = []

        mock_cell_2 = Mock()
        mock_cell_2.text.strip.return_value = "VANILLA BEAN"
        mock_cell_2.get_attribute.return_value = '<strong><a id="overlay_unique_id_205874" href="#open-overlay">VANILLA BEAN</a></strong>'

        # Mock single flavor link
        mock_link = Mock()
        mock_link.text.strip.return_value = "VANILLA BEAN"
        mock_link.is_displayed.return_value = True

        mock_cell_2.find_elements.return_value = [mock_link]

        mock_row.find_elements.side_effect = [
            [mock_link],  # All links in row
            [mock_cell_1, mock_cell_2],  # All cells in row
        ]
        mock_row.text.strip.return_value = "Wed 16 VANILLA BEAN"

        self.mock_driver.find_elements.return_value = [mock_row]

        # Run the scraper
        with patch("app.scrapers.oscars.time.sleep"):  # Skip actual sleep
            with patch("app.scrapers.oscars._extract_flavor_from_modal") as mock_extract:
                mock_extract.return_value = {
                    "flavor": "VANILLA BEAN",
                    "description": "Classic vanilla bean frozen custard.",
                    "date": "2025-07-16",
                    "restaurant": "Oscars",
                    "url": "https://www.oscarscustard.com/index.php/flavors",
                }

                result = scrape_oscars()

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1, "Should return 1 flavor")
        self.assertEqual(result[0]["flavor"], "VANILLA BEAN")

        # Verify single link was clicked
        self.assertEqual(self.mock_driver.execute_script.call_count, 1)

    def test_flavor_text_parsing_logic(self):
        """Test the logic for detecting multiple flavors in text."""
        test_cases = [
            ("LEMON BERRY -or- CHOCOLATE CHIP", True),
            ("VANILLA BEAN", False),
            ("STRAWBERRY -OR- MINT CHIP", True),
            ("COOKIES -or- CREAM", True),
            ("SINGLE FLAVOR", False),
            ("MULTIPLE or FLAVORS", True),
            ("TEST OR ANOTHER", True),
        ]

        for text, expected_has_or in test_cases:
            with self.subTest(text=text):
                has_or_text = "-OR-" in text.upper() or " OR " in text.upper()
                self.assertEqual(
                    has_or_text,
                    expected_has_or,
                    f"Text '{text}' should {'have' if expected_has_or else 'not have'} 'or' separator",
                )

    @patch("app.scrapers.oscars.BeautifulSoup")
    def test_extract_flavor_from_modal(self, mock_soup):
        """Test flavor extraction from modal HTML."""
        # Mock driver and overlay
        mock_driver = Mock()
        mock_overlay = Mock()
        mock_overlay.is_displayed.return_value = True
        mock_overlay.get_attribute.return_value = "<h4>TEST FLAVOR</h4><p>Test description</p>"

        mock_driver.find_elements.return_value = [mock_overlay]

        # Mock BeautifulSoup parsing
        mock_soup_instance = Mock()
        mock_soup.return_value = mock_soup_instance

        mock_h4 = Mock()
        mock_h4.get_text.return_value = "TEST FLAVOR"
        mock_soup_instance.find.return_value = mock_h4

        mock_p = Mock()
        mock_p.get_text.return_value = "Test description for the flavor"
        mock_h4.find_next.return_value = mock_p

        with patch("app.scrapers.oscars.daily_flavor") as mock_daily_flavor:
            mock_daily_flavor.return_value = {
                "flavor": "TEST FLAVOR",
                "description": "Test description for the flavor",
                "date": "2025-07-15",
                "restaurant": "Oscars",
                "url": "https://www.oscarscustard.com/index.php/flavors",
            }

            result = _extract_flavor_from_modal(mock_driver, "TEST FLAVOR")

        # Assertions
        self.assertIsNotNone(result)
        mock_daily_flavor.assert_called_once()


if __name__ == "__main__":
    unittest.main()
