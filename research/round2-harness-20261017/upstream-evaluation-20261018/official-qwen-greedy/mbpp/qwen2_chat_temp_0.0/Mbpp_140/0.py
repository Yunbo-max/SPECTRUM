def extract_singly(list_of_lists):
    """
    Flatten the list of lists into a single set of numbers.
    
    Args:
    list_of_lists (list of list of int): The list of lists to be flattened.
    
    Returns:
    set: A set containing all the unique numbers from the flattened list.
    """
    # Flatten the list of lists using list comprehension
    flattened_list = [num for sublist in list_of_lists for num in sublist]
    # Convert the flattened list to a set to remove duplicates
    unique_numbers = set(flattened_list)
    return unique_numbers