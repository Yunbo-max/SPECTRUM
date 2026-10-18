def change_date_format(date_str):
    # Split the date string into year, month, and day
    year, month, day = date_str.split('-')
    # Return the date in dd-mm-yyyy format
    return f"{day}-{month}-{year}"