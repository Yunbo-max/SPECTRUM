def count_first_elements(input_tuple):
    # Initialize a counter to keep track of the elements before the tuple
    count = 0
    # Iterate through the tuple
    for element in input_tuple:
        # If the element is a tuple, break the loop
        if isinstance(element, tuple):
            break
        # Increment the counter for each element before the tuple
        count += 1
    # Return the count of elements before the tuple
    return count