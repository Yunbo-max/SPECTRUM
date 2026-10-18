def snake_to_camel(snake_str):
    # Split the snake case string by underscore and capitalize each part
    camel_str = ''.join(word.capitalize() for word in snake_str.split('_'))
    return camel_str