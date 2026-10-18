def digit_distance_nums(num1, num2):
    # Convert the numbers to strings to easily access each digit
    str_num1 = str(num1)
    str_num2 = str(num2)
    
    # Initialize the sum of differences
    sum_diff = 0
    
    # Iterate over the digits of both numbers
    for i in range(len(str_num1)):
        # Calculate the absolute difference between the digits
        diff = abs(int(str_num1[i]) - int(str_num2[i]))
        # Add the difference to the sum
        sum_diff += diff
    
    # Return the total sum of differences
    return sum_diff