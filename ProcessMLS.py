"""Module should read .xls representations of MLS data, adding and removing information as necessary."""
import os
import sys
import pandas as pd
import math
import scipy.stats
import json
import numpy as np
from pandas.stats.api import ols

def GetHardCodedParameters():
	D = {'path_to_neighborhoods' : os.path.join("2015_0111_chicago_extraction"),
		'rooms_with_areas' : ['Mast Br Sz', '2nd Bdr Sz', '3rd Bdr Sz', '4th Bdr Sz', 'Addtl Rm 1 Sz', 
		'Addtl Rm 2 Sz', 'Addtl Rm 3 Sz', 'Addtl Rm 4 Sz', 'Addtl Rm 5 Sz', 'Din Sz', 'Fam Rm Sz',
		'Kit Sz', 'Liv Rm Sz'],
		'Data_Gathered_Year' : 2014,
		'MinExamples' : 10,
		'AgeRanges' : [(0,10),(11,50),(51,90),(91,999)]
		}
	return D

def GetAllFilesInDirectory(path_to_directory):
	return [f for f in os.listdir(path_to_directory) if os.path.isfile(os.path.join(path_to_directory,f))]
	
def GetMLS_file(path_to_directory, file_name):
	if os.path.exists(os.path.join(path_to_directory, file_name)):
		return pd.read_csv(os.path.join(path_to_directory, file_name))
	else:
		print("File for", file_name, "is unavailable")
		return None
	
def GetNonBathSquareFootage(D, single_property):
	rooms_to_examine = D['rooms_with_areas']
	square_footage = 0
	for room in rooms_to_examine:
		room_size_string = single_property[room]
		if type(room_size_string) == str:
			if 'X' in room_size_string: #if this room has a listed size
				square_footage += GetRoomArea(room_size_string)
	return square_footage
	
def GetRoomArea(room_size_string):
	"""For areas of the form '15X20', e.g."""
	dimensions = room_size_string.split('X')
	return int(dimensions[0]) * int(dimensions[1])

def ClassifyAge(D, property_data):
	NewAges = []
	for age, year_built in zip(property_data.Age, property_data['Yr Blt']):
		if year_built == 'NEW':
			NewAges.append(0)
		elif year_built != 'UNK' and not math.isnan(float(year_built)) and year_built != 0:
			NewAges.append(D['Data_Gathered_Year'] - int(year_built))
		elif type(age) != str: 
			if math.isnan(float(age)):
				NewAges.append(999)
		elif 'NEW' in age:
			NewAges.append(0)
		elif '-' in age:
			NewAges.append(int(age.split('-')[0]))
		elif '+' in age:
			NewAges.append(int(age.split('+')[0]))
		else:
			NewAges.append(999)
	property_data['MinAge'] = NewAges
	return property_data

def ClassifyPropertyType(property_data):
	NewTypes = []
	for property_type in property_data.Type:
		if type(property_type) != str:
			NewTypes.append('UNKNOWN')
		elif 'Townhouse' in property_type or 'Duplex' in property_type:
			NewTypes.append('Townhouse')
		elif 'High' in property_type:
			NewTypes.append('HighRise')
		elif 'Mid' in property_type or 'Low' in property_type:
			NewTypes.append('LowRise')
		elif 'Stories' in property_type and len(property_type) < 12:
			NewTypes.append('Detached')
		elif 'Condo' in property_type or 'Studio' in property_type:
			NewTypes.append('Condo')
		else:
			NewTypes.append('UNKNOWN')
	property_data['GroupType'] = NewTypes
	return property_data
	
def unique(seq):
	"""Given a list, return a list of all unique elements...like the 'unique' command in R.  Works for python 3.4."""
	seen = []
	return [c for c in seq if not (c in seen or seen.append(c))]	
	
def Cluster_and_add_Columns(D, property_data, file_name):
	if 'MinAge' not in property_data.columns:
		property_data = ClassifyAge(D, property_data)
	if 'GroupType' not in property_data.columns:
		property_data = ClassifyPropertyType(property_data)
	property_data = AddNeighborhood(property_data, file_name)
	return property_data

def AddNeighborhood(property_data, file_name):
	neighborhood = file_name.split(' - ')[0]  
	property_data['Neighborhood'] = [neighborhood for i in range(len(property_data))]
	return property_data
	
def CleanAllProperties(all_property_data, path_to_directory):
	cleaned_properties = {}
	for column_name in all_property_data.columns:
		cleaned_properties[column_name] = []
		for value in all_property_data[column_name]:
			cleaned_properties[column_name].append(value)
	if not os.path.exists(os.path.join(path_to_directory, 'clean_data')):
		os.makedirs(os.path.join(path_to_directory, 'clean_data'))
	with open(os.path.join(path_to_directory, 'clean_data', 'all_properties.json'), 'wt') as outfile:
		json.dump(cleaned_properties, outfile)
	return None
	
def GetSimilarAge_and_Group(all_property_data, neighborhood, min_age, max_age, group_type):
	sub_property_data = all_property_data[all_property_data.Neighborhood == neighborhood]
	sub_property_data.index = range(len(sub_property_data))
	sub_property_data = sub_property_data[np.logical_and(sub_property_data.MinAge >= min_age,
														 sub_property_data.MinAge <= max_age)]
	return sub_property_data[sub_property_data.GroupType == group_type]
		
def GetCostPerSQFT_and_intercept(sub_property_data):
	res = ols(x=sub_property_data.ASF, y=sub_property_data['List Price'])
	#return the intercept, the x-coefficient (cost per additional sqft), correlation coefficient
	return int(res.beta.intercept), round(res.beta.x,2), round(math.sqrt(res.r2),3)

def BuildAllPropertyData(path_to_directory):
	all_MLS_files = GetAllFilesInDirectory(path_to_directory)	
	for i, file_name in enumerate(all_MLS_files):
		print("Processing", file_name)
		property_data = GetMLS_file(path_to_directory, file_name)
		if i == 0: #the first such neighborhood
			all_property_data = Cluster_and_add_Columns(D, property_data, file_name)
		else:
			all_property_data = all_property_data.append(Cluster_and_add_Columns(D, property_data, file_name))
	return all_property_data
	
def main():
	D = GetHardCodedParameters()
	path_to_directory = D['path_to_neighborhoods']
	all_property_data = BuildAllPropertyData(path_to_directory)
	group_types = unique(all_property_data.GroupType)	
		
	return None
	
if __name__ == "__main__"
	null = sys.argv
	main()