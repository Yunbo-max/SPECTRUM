def frequency_lists(list_of_lists):
    # Flatten the list of lists
    flattened_list = [item for sublist in list_of_lists for item in sublist]
    # Create a dictionary to store the frequency of each element
    frequency_dict = {}
    for item in flattened_list:
        if item in frequency_dict:
            frequency_dict[item] += 1
        else:
            frequency_dict[item] = 1
    return frequency_dict