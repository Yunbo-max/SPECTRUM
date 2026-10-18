def pair_wise(lst):
    # Initialize an empty list to store the pairs
    pairs = []
    # Iterate through the list, stopping one element before the end
    for i in range(len(lst) - 1):
        # Append a tuple containing the current element and the next element
        pairs.append((lst[i], lst[i + 1]))
    # Return the list of pairs
    return pairs