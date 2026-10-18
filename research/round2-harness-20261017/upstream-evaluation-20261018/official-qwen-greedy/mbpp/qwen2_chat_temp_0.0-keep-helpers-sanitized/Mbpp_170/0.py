def sum_range_list(lst, start, end):
    # Initialize the sum to 0
    total_sum = 0
    # Iterate through the list from the start index to the end index
    for i in range(start, end + 1):
        # Add each number in the range to the total sum
        total_sum += lst[i]
    # Return the total sum of the numbers in the specified range
    return total_sum