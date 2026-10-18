def sort_sublists(lst):
    # Use list comprehension to iterate through each sublist in the list
    # Apply the sorted function to each sublist to sort the strings
    return [sorted(sublist) for sublist in lst]