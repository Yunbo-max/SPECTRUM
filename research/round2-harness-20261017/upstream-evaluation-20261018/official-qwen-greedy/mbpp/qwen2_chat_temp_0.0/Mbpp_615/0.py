def average_tuple(tuples):
    # Initialize an empty list to store the average values
    averages = []
    # Iterate over each tuple in the input list
    for tup in tuples:
        # Calculate the sum of the elements in the tuple
        total = sum(tup)
        # Calculate the average by dividing the sum by the number of elements
        average = total / len(tup)
        # Append the average to the list of averages
        averages.append(average)
    # Return the list of averages
    return averages