def sort_sublists(list_of_lists):
    # Iterate through each sublist in the list of lists
    for sublist in list_of_lists:
        # Sort the sublist in ascending order
        sublist.sort()
    # Return the modified list of lists
    return list_of_lists