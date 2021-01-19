def safeAppend(D, key, val):
    """Given a dictionary (D), if the (key) exists, append the (val) to its list.
    Otherwise, create the key and instantiate a list with the single value."""
    if key in D:
        D[key].append(val)
    else:
        D[key] = [val]