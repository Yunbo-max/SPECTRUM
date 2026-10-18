def test_duplicate(arr):
    # Create a set to store unique elements
    unique_elements = set()
    # Iterate through each element in the array
    for element in arr:
        # If the element is already in the set, it's a duplicate
        if element in unique_elements:
            return True
        # Add the element to the set
        unique_elements.add(element)
    # If no duplicates are found, return False
    return False