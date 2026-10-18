def first_odd(numbers):
    # Iterate through the list of numbers
    for num in numbers:
        # Check if the number is odd
        if num % 2 != 0:
            # Return the first odd number found
            return num
    # If no odd number is found, return None
    return None