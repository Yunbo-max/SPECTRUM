def max_product(arr):
    # Initialize the maximum product to 1
    max_product = 1
    # Initialize the current product to 1
    current_product = 1
    
    # Iterate through the array
    for num in arr:
        # If the current product is less than 1, reset it to 1
        if current_product < 1:
            current_product = 1
        # Multiply the current product by the current number
        current_product *= num
        # Update the maximum product if the current product is greater
        max_product = max(max_product, current_product)
    
    return max_product