def extract_even(mixed_tuple):
    # Initialize an empty list to store even elements
    even_elements = []
    # Iterate through each element in the mixed tuple
    for element in mixed_tuple:
        # Check if the element is a tuple
        if isinstance(element, tuple):
            # Recursively call the function on the nested tuple
            even_elements.extend(extract_even(element))
        # Check if the element is an integer and even
        elif isinstance(element, int) and element % 2 == 0:
            # Append the even integer to the list
            even_elements.append(element)
    # Return the list of even elements
    return tuple(even_elements)