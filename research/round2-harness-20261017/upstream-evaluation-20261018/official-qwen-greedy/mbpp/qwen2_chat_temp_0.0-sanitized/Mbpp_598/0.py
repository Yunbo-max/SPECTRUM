def armstrong_number(n):
    # Convert the number to a string to easily iterate over each digit
    num_str = str(n)
    # Calculate the number of digits in the number
    num_digits = len(num_str)
    # Initialize the sum of the cubes of the digits
    sum_of_cubes = 0
    # Iterate over each digit in the number
    for digit in num_str:
        # Convert the digit back to an integer and cube it
        digit_cubed = int(digit) ** num_digits
        # Add the cube of the digit to the sum
        sum_of_cubes += digit_cubed
    # Check if the sum of the cubes is equal to the original number
    return sum_of_cubes == n