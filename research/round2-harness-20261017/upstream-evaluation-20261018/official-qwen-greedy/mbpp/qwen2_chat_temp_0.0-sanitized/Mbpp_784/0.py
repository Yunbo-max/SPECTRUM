def mul_even_odd(lst):
    # Initialize variables to store the product of even and odd numbers
    even_product = 1
    odd_product = 1
    
    # Iterate through the list to find even and odd numbers
    for num in lst:
        if num % 2 == 0:
            even_product *= num
        else:
            odd_product *= num
    
    # Return the product of even and odd numbers
    return even_product * odd_product