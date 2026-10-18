def division_elements(tuple1, tuple2):
    # Using list comprehension to perform element-wise division
    result = tuple(a / b for a, b in zip(tuple1, tuple2))
    return result