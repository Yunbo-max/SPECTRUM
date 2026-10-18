def freq_count(lst):
    # Initialize an empty dictionary to store the frequency of each element
    freq_dict = {}
    # Iterate through each element in the list
    for element in lst:
        # If the element is already in the dictionary, increment its count
        if element in freq_dict:
            freq_dict[element] += 1
        # If the element is not in the dictionary, add it with a count of 1
        else:
            freq_dict[element] = 1
    # Return the dictionary containing the frequency of each element
    return freq_dict