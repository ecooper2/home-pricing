def FixNonUTFCompliantCSV(path_to_directory, file_name):
    f = open(os.path.join(path_to_directory, file_name)).readlines()
    column_names = f[0].split(',')
    all_listings = {}
    for column_name in column_names:
        all_listings[column_name] = []
    for line in f[2:]:
        split_line = line.split(',')
        for column_name, value in zip(column_names, split_line):
            all_listings[column_name].append(value)
    listings = pd.DataFrame(all_listings)
    listings.to_csv(os.path.join(path_to_directory, file_name), index = False)
    return listings

def AddNonBathSquareFootage(D, property_data, neighborhood):
    non_bath_sqft = []
    for i in range(len(property_data)):
        non_bath_sqft.append(GetNonBathSquareFootage(D, property_data.ix[i]))
    property_data['non_bath_sqft'] = non_bath_sqft
    return property_data
