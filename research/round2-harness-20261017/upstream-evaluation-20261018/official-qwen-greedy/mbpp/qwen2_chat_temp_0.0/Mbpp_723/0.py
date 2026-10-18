def count_same_pair(list1, list2):
    # Initialize a counter for matching pairs
    count = 0
    # Iterate through the lists using zip to pair elements from both lists
    for i, j in zip(list1, list2):
        # If the elements are the same, increment the counter
        if i == j:
            count += 1
    # Return the total count of matching pairs
    return count