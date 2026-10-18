def assert_and_tuples(tup1, tup2):
    # Extracting elements and tuples from the given tuples
    result = tuple(x - y for x, y in zip(tup1, tup2))
    return result