def check_element(lst, element):
    # Check if all elements in the list are equal to the given element
    return all(item == element for item in lst)