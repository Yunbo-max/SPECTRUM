def Split(numbers):
    # Initialize an empty list to store even numbers
    even_numbers = []
    # Iterate through each number in the input list
    for num in numbers:
        # Check if the number is even
        if num % 2 == 0:
            # If even, append it to the even_numbers list
            even_numbers.append(num)
    # Return the list of even numbers
    return even_numbers