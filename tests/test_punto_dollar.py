import unittest
from unittest.mock import patch

from exchanges.puntoDollar import puntoDollar


class PuntoDollarParsingTests(unittest.TestCase):
    def test_three_digits_after_separator_are_treated_as_thousands(self):
        html = """
        <table>
            <tr><th>Moneda</th><th>Compra</th><th>Venta</th></tr>
            <tr><td>US Dolar Americano</td><td>2,600</td><td>2.60</td></tr>
        </table>
        """

        with patch("exchanges.puntoDollar.requests.get") as get:
            get.return_value.text = html

            result = puntoDollar("https://example.test", local="Bogota")

        data = result[0]["data"]["US Dolar Americano"]
        self.assertEqual("2600", data["buy"])
        self.assertEqual("2,60", data["sell"])


if __name__ == "__main__":
    unittest.main()
