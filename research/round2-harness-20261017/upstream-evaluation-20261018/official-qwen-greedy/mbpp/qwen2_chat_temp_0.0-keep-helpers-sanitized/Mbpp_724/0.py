def power_base_sum(base, power):
    # Calculate the base raised to the power
    result = base ** power
    # Convert the result to a string to iterate over each digit
    result_str = str(result)
    # Initialize the sum of digits
    sum_of_digits = 0
    # Iterate over each digit in the string
    for digit in result_str:
        # Convert the digit back to an integer and add it to the sum
        sum_of_digits += int(digit)
    # Return the sum of digits
    return sum_of_digits