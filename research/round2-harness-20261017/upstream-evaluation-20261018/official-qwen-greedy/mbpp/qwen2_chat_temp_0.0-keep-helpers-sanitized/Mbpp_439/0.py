def multiple_to_single(numbers):
    # Convert each integer in the list to a string and concatenate them
    concatenated_string = ''.join(str(num) for num in numbers)
    # Convert the concatenated string back to an integer
    return int(concatenated_string)