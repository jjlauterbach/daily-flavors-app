import unittest

from app.scrapers.bubbas import scrape_bubbas
from app.scrapers.culvers import scrape_culvers
from app.scrapers.kopps import scrape_kopps
from app.scrapers.murfs import scrape_murfs
from app.scrapers.oscars import scrape_oscars
from conftest import ecosystem


class TestScraperEcosystem(unittest.TestCase):
    @ecosystem
    def test_each_scraper_returns_flavor(self):
        """Test that each scraper returns at least one flavor with required fields."""
        scrapers = [
            ("Culvers", scrape_culvers),
            ("Kopps", scrape_kopps),
            ("Murfs", scrape_murfs),
            ("Oscars", scrape_oscars),
            ("Bubbas", scrape_bubbas),
        ]
        for name, scraper in scrapers:
            with self.subTest(scraper=name):
                results = scraper()
                self.assertIsInstance(results, list, f"{name} did not return a list")
                self.assertGreater(len(results), 0, f"{name} returned no flavors")
                for flavor in results:
                    self.assertTrue(flavor.get("flavor"), f"{name} flavor missing")
                    self.assertTrue(flavor.get("date"), f"{name} date missing")
                    self.assertIn("description", flavor, f"{name} description missing")


if __name__ == "__main__":
    unittest.main()
