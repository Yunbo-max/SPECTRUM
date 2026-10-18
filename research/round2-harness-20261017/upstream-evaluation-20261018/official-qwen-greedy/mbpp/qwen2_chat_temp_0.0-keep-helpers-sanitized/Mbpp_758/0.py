def unique_sublists(lst):
    # Convert each sublist to a tuple and count occurrences
    return {tuple(sublist): lst.count(sublist) for sublist in lst}