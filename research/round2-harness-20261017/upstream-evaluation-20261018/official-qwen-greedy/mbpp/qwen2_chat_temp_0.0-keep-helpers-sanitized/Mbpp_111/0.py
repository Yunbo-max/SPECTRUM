def common_in_nested_lists(nested_lists):
    # Initialize an empty set to store common elements
    common_elements = set()
    # Iterate over each sublist in the nested lists
    for sublist in nested_lists:
        # Iterate over each element in the sublist
        for element in sublist:
            # Add the element to the common_elements set if it is already present
            if element in common_elements:
                continue
            # Add the element to the common_elements set
            common_elements.add(element)
    # Return the set of common elements
    return common_elements