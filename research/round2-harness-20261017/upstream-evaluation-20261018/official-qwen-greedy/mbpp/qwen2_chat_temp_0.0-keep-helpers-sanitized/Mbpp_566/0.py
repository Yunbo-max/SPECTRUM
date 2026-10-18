def sum_digits(n):
    # Initialize the sum to 0
    total_sum = 0
    # Loop through each digit in the number
    while n > 0:
        # Add the last digit to the total sum
        total_sum += n % 10
        # Remove the last digit from the number
        n //= 10
    # Return the total sum of the digits
    return total_sum