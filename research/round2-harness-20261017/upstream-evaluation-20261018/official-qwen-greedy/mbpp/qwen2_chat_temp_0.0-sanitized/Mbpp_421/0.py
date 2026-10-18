def concatenate_tuple(tup, delimiter):
    # Initialize an empty string to store the concatenated result
    result = ""
    # Iterate over each element in the tuple
    for element in tup:
        # Convert the element to a string and concatenate it with the delimiter
        result += str(element) + delimiter
    # Return the concatenated string
    return result