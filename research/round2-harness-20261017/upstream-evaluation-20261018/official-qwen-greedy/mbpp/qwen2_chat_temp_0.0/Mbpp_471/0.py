def find_remainder(arr, n):
    # Initialize the product to 1
    product = 1
    
    # Iterate through each element in the array
    for num in arr:
        # Multiply the product by the current number and take modulo n
        product = (product * num) % n
    
    # Return the final product
    return product