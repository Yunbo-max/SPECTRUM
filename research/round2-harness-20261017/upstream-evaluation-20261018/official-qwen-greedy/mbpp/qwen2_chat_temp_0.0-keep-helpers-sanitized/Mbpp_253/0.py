def count_integer(lst):
    # Initialize a counter for integer elements
    count = 0
    # Iterate through each element in the list
    for element in lst:
        # Check if the element is an integer
        if isinstance(element, int):
            # Increment the counter if the element is an integer
            count += 1
    # Return the total count of integer elements
    return count