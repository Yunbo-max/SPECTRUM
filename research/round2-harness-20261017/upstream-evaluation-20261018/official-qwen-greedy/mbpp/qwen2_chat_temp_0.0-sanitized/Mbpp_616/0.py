def tuple_modulo(tuple1, tuple2):
    # Use the map function to apply the modulo operation to each pair of elements
    result = tuple(map(lambda x, y: x % y, tuple1, tuple2))
    return result