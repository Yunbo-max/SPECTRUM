def sum_even_and_even_index(lst):
    # Initialize the sum to 0
    total_sum = 0
    # Iterate through the list, starting from the second element (index 1) and incrementing by 2
    for i in range(1, len(lst), 2):
        # Check if the element at the current index is even
        if lst[i] % 2 == 0:
            # Add the even number to the total sum
            total_sum += lst[i]
    # Return the total sum of even numbers at even positions
    return total_sum