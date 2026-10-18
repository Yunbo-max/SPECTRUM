def min_product_tuple(tuples_list):
    # Initialize the minimum product to a large number
    min_product = float('inf')
    # Iterate through each tuple in the list
    for tup in tuples_list:
        # Calculate the product of the two numbers in the tuple
        product = tup[0] * tup[1]
        # Update the minimum product if the current product is smaller
        if product < min_product:
            min_product = product
    # Return the minimum product found
    return min_product