def pack_consecutive_duplicates(lst):
    # Initialize an empty list to store the result
    result = []
    # Initialize an empty list to store the current sublist
    current_sublist = []
    # Iterate through the given list
    for i in range(len(lst)):
        # If the current element is the same as the previous element, add it to the current sublist
        if i > 0 and lst[i] == lst[i-1]:
            current_sublist.append(lst[i])
        # If the current element is different from the previous element, add the current sublist to the result and start a new sublist
        else:
            result.append(current_sublist)
            current_sublist = [lst[i]]
    # Add the last sublist to the result
    result.append(current_sublist)
    return result