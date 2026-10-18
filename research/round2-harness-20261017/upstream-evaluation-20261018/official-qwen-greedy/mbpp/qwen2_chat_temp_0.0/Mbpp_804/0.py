def is_product_even(numbers):
    # Calculate the product of all numbers in the list
    product = 1
    for num in numbers:
        product *= num
    
    # Check if the product is even
    return product % 2 == 0