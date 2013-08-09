def value_in_range(value, small, big):
    if value >= small and value <= big:
        return value
    else:
        raise ValueError('Value out of range')
