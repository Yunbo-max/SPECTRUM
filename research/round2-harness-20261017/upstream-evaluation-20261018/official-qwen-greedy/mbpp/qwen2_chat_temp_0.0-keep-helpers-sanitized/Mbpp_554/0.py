def Split(numbers):
    # Initialize an empty list to store odd numbers
    odd_numbers = []
    # Iterate through each number in the input list
    for num in numbers:
        # Check if the number is odd
        if num % 2 != 0:
            # If odd, append it to the odd_numbers list
            odd_numbers.append(num)
    # Return the list of odd numbers
    return odd_numbers