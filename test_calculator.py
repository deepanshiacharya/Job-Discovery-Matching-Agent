import unittest
from calculator import add, subtract, multiply, divide, format_number


class TestCalculator(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(add(10, 5), 15)
        self.assertEqual(add(-1, 1), 0)
        self.assertAlmostEqual(add(0.1, 0.2), 0.3, places=7)

    def test_subtraction(self):
        self.assertEqual(subtract(10, 5), 5)
        self.assertEqual(subtract(5, 10), -5)
        self.assertEqual(subtract(-2, -3), 1)

    def test_multiplication(self):
        self.assertEqual(multiply(6, 7), 42)
        self.assertEqual(multiply(-3, 4), -12)
        self.assertEqual(multiply(0, 100), 0)

    def test_division(self):
        self.assertEqual(divide(10, 2), 5)
        self.assertEqual(divide(9, 2), 4.5)
        self.assertEqual(divide(-12, 3), -4)

    def test_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            divide(10, 0)

    def test_format_number(self):
        self.assertEqual(format_number(5.0), "5")
        self.assertEqual(format_number(5.5), "5.5")


if __name__ == "__main__":
    unittest.main()
