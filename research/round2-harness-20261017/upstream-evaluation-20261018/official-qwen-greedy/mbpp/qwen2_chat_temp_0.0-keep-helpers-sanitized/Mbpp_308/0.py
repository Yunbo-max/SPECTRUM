def large_product(list1, list2, n):
    # Sort both lists in descending order
    list1.sort(reverse=True)
    list2.sort(reverse=True)
    
    # Initialize an empty list to store the largest products
    largest_products = []
    
    # Iterate through the first n elements of list1
    for i in range(n):
        # Multiply the current element of list1 with the first element of list2
        product = list1[i] * list2[0]
        # Append the product to the list of largest products
        largest_products.append(product)
    
    # Return the list of largest products
    return largest_products