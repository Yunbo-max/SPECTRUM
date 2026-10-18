def return_sum(dictionary):
    # Initialize the sum to 0
    total_sum = 0
    # Iterate over each key-value pair in the dictionary
    for key, value in dictionary.items():
        # Add the value to the total sum
        total_sum += value
    # Return the total sum
    return total_sum