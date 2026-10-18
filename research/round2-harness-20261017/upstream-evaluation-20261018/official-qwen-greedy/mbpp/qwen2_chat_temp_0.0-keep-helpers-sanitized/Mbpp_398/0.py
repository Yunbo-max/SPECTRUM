def sum_of_digits(numbers):
    # Initialize the sum to 0
    total_sum = 0
    # Iterate through each number in the list
    for num in numbers:
        # Convert the number to a string to iterate through each digit
        for digit in str(num):
            # Convert the digit back to an integer and add it to the total sum
            total_sum += int(digit)
    # Return the total sum of digits
    return total_sum