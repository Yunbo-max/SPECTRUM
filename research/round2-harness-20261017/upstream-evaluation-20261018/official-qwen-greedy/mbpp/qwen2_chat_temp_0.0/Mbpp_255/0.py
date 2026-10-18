def combinations_colors(colors, n):
    """
    Generate all combinations (with repetition) of the elements of the list and return a list with a tuple for each combination.
    
    :param colors: List of colors
    :param n: Length of each combination
    :return: List of tuples representing all combinations
    """
    # Initialize an empty list to store the combinations
    combinations = []
    
    # Generate combinations using itertools.product
    for combination in itertools.product(colors, repeat=n):
        # Append each combination as a tuple to the list
        combinations.append(tuple(combination))
    
    return combinations