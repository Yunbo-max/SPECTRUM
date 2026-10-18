def text_lowercase_underscore(text):
    # Split the text by underscore and check if all parts are lowercase
    return all(part.islower() for part in text.split('_'))