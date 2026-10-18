def interleave_lists(list1, list2, list3):
    # Initialize an empty list to store the interleaved elements
    interleaved_list = []
    # Iterate over the indices of the lists
    for i in range(len(list1)):
        # Append elements from each list in order
        interleaved_list.append(list1[i])
        interleaved_list.append(list2[i])
        interleaved_list.append(list3[i])
    # Return the interleaved list
    return interleaved_list