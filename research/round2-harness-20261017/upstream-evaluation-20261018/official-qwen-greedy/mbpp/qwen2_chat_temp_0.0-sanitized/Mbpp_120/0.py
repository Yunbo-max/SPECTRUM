def max_product_tuple(tuples_list):
    # Initialize the maximum product to a very small number
    max_product = float('-inf')
    
    # Iterate through each tuple in the list
    for tup in tuples_list:
        # Calculate the product of the two numbers in the tuple
        product = tup[0] * tup[1]
        # Update the maximum product if the current product is greater
        if product > max_product:
            max_product = product
    
    # Return the maximum product found
    return max_product