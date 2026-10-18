def pos_count(lst):
    # Initialize a counter for positive numbers
    count = 0
    # Iterate through each number in the list
    for num in lst:
        # Check if the number is positive
        if num > 0:
            # Increment the counter if the number is positive
            count += 1
    # Return the total count of positive numbers
    return count