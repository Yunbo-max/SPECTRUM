import math

def multiply_num(nums):
    # Calculate the product of all numbers in the list
    product = 1
    for num in nums:
        product *= num
    
    # Calculate the length of the list
    length = len(nums)
    
    # Divide the product by the length of the list
    result = product / length
    
    return result