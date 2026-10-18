def round_and_sum(numbers):
    # Round each number in the list
    rounded_numbers = [round(num) for num in numbers]
    # Calculate the total sum of the rounded numbers
    total_sum = sum(rounded_numbers)
    # Calculate the length of the list
    list_length = len(numbers)
    # Return the total sum multiplied by the length of the list
    return total_sum * list_length