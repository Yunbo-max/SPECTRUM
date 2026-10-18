def count_samepair(list1, list2, list3):
    # Initialize a counter for identical pairs
    count = 0
    # Iterate through the lists
    for i in range(len(list1)):
        # Check if the elements at the current position are identical
        if list1[i] == list2[i] == list3[i]:
            # Increment the counter if the condition is met
            count += 1
    # Return the total count of identical pairs
    return count