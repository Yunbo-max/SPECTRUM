def max_Product(arr):
    # Initialize the maximum product to negative infinity
    max_product = float('-inf')
    # Initialize the first and second maximum numbers to negative infinity
    first_max = float('-inf')
    second_max = float('-inf')
    
    # Iterate through the array
    for num in arr:
        # Update the maximum product
        if num > max_product:
            max_product = num
        # Update the first maximum number
        elif num > first_max:
            second_max = first_max
            first_max = num
        # Update the second maximum number if it's less than the first maximum but greater than the second maximum
        elif num > second_max and num != first_max:
            second_max = num
    
    # Return the pair with the highest product
    return (first_max, second_max)