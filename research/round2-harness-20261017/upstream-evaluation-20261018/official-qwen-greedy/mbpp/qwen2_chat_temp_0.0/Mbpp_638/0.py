def wind_chill(wind_velocity, temperature):
    # Calculate the wind chill index using the formula
    wind_chill_index = 13.12 + 0.6215 * temperature - 11.37 * (wind_velocity ** 0.16) + 0.3965 * temperature * (wind_velocity ** 0.16)
    # Round the result to the next integer
    return round(wind_chill_index)