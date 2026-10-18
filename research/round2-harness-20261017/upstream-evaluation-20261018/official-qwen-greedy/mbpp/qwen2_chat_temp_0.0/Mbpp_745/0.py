def divisible_by_digits(startnum, endnum):
    # Initialize an empty list to store numbers that meet the criteria
    result = []
    # Iterate through each number in the given range
    for num in range(startnum, endnum + 1):
        # Convert the number to a string to easily iterate over each digit
        num_str = str(num)
        # Check if the number is divisible by every digit it contains
        if all(int(digit) != 0 and num % int(digit) == 0 for digit in num_str):
            # If the condition is met, add the number to the result list
            result.append(num)
    # Return the list of numbers that meet the criteria
    return result