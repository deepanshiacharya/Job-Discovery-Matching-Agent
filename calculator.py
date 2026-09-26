"""A simple interactive command-line calculator supporting basic arithmetic operations."""

def add(x: float, y: float) -> float:
    """Return the sum of x and y."""
    return x + y


def subtract(x: float, y: float) -> float:
    """Return the difference of x and y."""
    return x - y


def multiply(x: float, y: float) -> float:
    """Return the product of x and y."""
    return x * y


def divide(x: float, y: float) -> float:
    """Return the quotient of x and y.

    Raises:
        ZeroDivisionError: If y is zero.
    """
    if y == 0:
        raise ZeroDivisionError("Cannot divide by zero.")
    return x / y


def format_number(val: float) -> str:
    """Format number to remove unnecessary trailing decimals."""
    if val.is_integer():
        return str(int(val))
    return f"{val:.6g}"


def get_number(prompt: str) -> float:
    """Prompt the user for a valid number with retry handling."""
    while True:
        raw_val = input(prompt).strip()
        try:
            return float(raw_val)
        except ValueError:
            print("Invalid input! Please enter a valid numerical value.")


def main():
    operations = {
        "1": ("+", "Addition", add),
        "2": ("-", "Subtraction", subtract),
        "3": ("*", "Multiplication", multiply),
        "4": ("/", "Division", divide),
    }

    print("=" * 35)
    print("         PYTHON CALCULATOR         ")
    print("=" * 35)

    while True:
        print("\nSelect an operation:")
        for key, (symbol, name, _) in operations.items():
            print(f"  [{key}] {name} ({symbol})")
        print("  [5] Exit")

        choice = input("\nEnter choice (1-5): ").strip()

        if choice == "5":
            print("\nThank you for using the calculator. Goodbye!")
            break

        if choice not in operations:
            print("Invalid choice! Please select an option from 1 to 5.")
            continue

        symbol, name, func = operations[choice]

        num1 = get_number("\nEnter first number: ")
        num2 = get_number("Enter second number: ")

        try:
            result = func(num1, num2)
            n1_str = format_number(num1)
            n2_str = format_number(num2)
            res_str = format_number(result)
            print(f"\nResult: {n1_str} {symbol} {n2_str} = {res_str}")
        except ZeroDivisionError as err:
            print(f"\nError: {err}")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
