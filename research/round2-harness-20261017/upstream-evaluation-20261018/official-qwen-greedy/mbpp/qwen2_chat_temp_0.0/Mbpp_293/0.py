import math

def otherside_rightangle(a, b):
    # Calculate the square of the hypotenuse
    hypotenuse_squared = a**2 + b**2
    # Calculate the square root of the hypotenuse to find the length of the third side
    third_side = math.sqrt(hypotenuse_squared)
    return third_side