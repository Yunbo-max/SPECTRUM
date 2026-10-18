def unique_product(numbers):
    # Create a set to store unique numbers
    unique_numbers = set(numbers)
    # Calculate the product of the unique numbers
    product = 1
    for number in unique_numbers:
        product *= number
    return product