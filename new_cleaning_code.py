import sys,os
import PySide2

dirname = os.path.dirname(PySide2.__file__)
plugin_path = os.path.join(dirname, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

import PySimpleGUI as sg
import pandas as pd
import numpy as np
import datetime
import calendar
import openpyxl
import collections, csv
import os
import linecache

atr_dict = {
    "070E214 I-70 E/B JOHNSON / EISENHOWER TUNNEL": "I-70 EJMT",
    "070W216 I-70 W/B EISENHOWER / JOHNSON TUNNEL": "I-70 EJMT",
    
    "225N011 SH 225 S/O I-70 - N/O COLFAX": "I-225 North of Colfax",
    "025N209 I-25 S/O 6TH AVE. N/B ( DENVER )": "I-25 South of 6th Ave",
    "025N209 I-25 S/O 6TH AVE. S/B ( DENVER )": "I-25 South of 6th Ave",
    
    "025N230 I-25 N/O SH 7 INTERCHANGE": "I-25 Broomfield",
    
    # Possibly try to map the new device names to I-25 Loveland as well
    "000N256 I-25 S/O SH 34 INTERCHANGE (LOVELAND)": "I-25 Loveland",
    "000N256 I-25 S/O SH 34 INTERCHANGE (LOVELAND)_REMOVED_2020-12-30 12:08:38.958": "I-25 Loveland",
    "025N272 I-25 N/O FORT COLLINS": "I-25 Fort Collins",
    
    "076E012 ON I-76 SW/O 88TH AVE, COMMERCE CITYON I-76 SW/O 88TH AVE, COMMERCE CITY": "I-76 Commerce City",
    "076E040 ON I-76 EN/O SH 76 SPUR, MARKET ST, KEENESBURG": "I-76 Keenesburg",
    "160E084 SH 160 E/O SANTA RITA, DURANGO": "US-160 Durango",
    "287N319 SH 287 N/O LONGMONT": "US-287 Longmont",
    "036E044 SH 36 E/O SUPERIOR": "US-36 Superior",
    "036E049 ON SH 36 SE/O SH 121, WADSWORTH PKWY, BROOMFIELD": "US-36 Broomfield",
    "050E318 SH 50 NW/O SH 96 / 47 PUEBLO": "US-50 Pueblo",
    "550N119 ON SH 550 SW/O VERNAL RD, MONTROSE": "US-550 Montrose",
    "085N135 ON SH 85 SE/O B ST, COLORADO SPRINGS": "US-85 Colorado Springs",
}

primary_dir_dict = {
    'I-70 EJMT': "East",
    'I-25 Broomfield': "North",
    'I-25 Loveland': "North",
    'I-25 South of 6th Ave': "North",
    'US-50 Pueblo': "East",
    'I-225 North of Colfax': "North",
    'I-76 Commerce City' : "East",
    'I-76 Keenesburg' : "East",
    'US-36 Broomfield': "East",
    'US-36 Superior': "East",
    'US-287 Longmont' : "North",
    'US-85 Colorado Springs': "North",
    'US-160 Durango': "East",
    'US-550 Montrose': "North"
    }

secondary_dir_dict = {
    'I-70 EJMT': "West",
    'I-25 Broomfield': "South",
    'I-25 Loveland': "South",
    'I-25 South of 6th Ave': "South",
    'US-50 Pueblo': "West",
    'I-225 North of Colfax': "South",
    'I-76 Commerce City' : "West",
    'I-76 Keenesburg' : "West",
    'US-36 Broomfield': "West",
    'US-36 Superior': "West",
    'US-287 Longmont' : "South",
    'US-85 Colorado Springs': "South",
    'US-160 Durango': "West",
    'US-550 Montrose': "South"
    }

def data_frame_cleaner(df, atr_dict):
    '''
        Purpose: read in COGNOS ATR Report and reformat it.
        INPUTS:
            df: Cognos export file read in as a pandas df
            atr_dict: A dictionary of ATR names
        OUTPUT:
            dataframe with date/time and location name columns appended
    '''
    # Extract the columns needed
    df = df[[
        "Date Time Start Short", 
        "Road", 
        "Device", 
        "Site ID", 
        "Hour", 
        "Lane Direction", 
        "Lane #", 
        "Total Volume"
    ]]

    # Transform the date into separate columns with date components
    df["Date"] = df["Date Time Start Short"].apply(
        lambda x: x.split(" ")[0]
        )
    df["Date"] = pd.to_datetime(df["Date"])

    df["Weeknum"] = df["Date"].dt.isocalendar().week

    df["Weekday"] = df["Date"].apply(
        lambda x: datetime.datetime.strftime(x, '%A')
        )

    df["Year"] = df["Date"].dt.isocalendar().year

    # # Rename volume column
    # df.rename(
    #             columns = {
    #                 "Total Volume": "{} Volume".format(year_string)
    #                 },
    #             inplace=True
    #             )
    # Map the ATR names to the df

    df['Location Name'] = df['Device'].map(atr_dict)

    return df


def time_spanner(df, date_column):
    ''' 
    PURPOSE: Create an empty date range spanning the start and end timestamp of your file
        in 1 hour increments.
    '''
    start_date = min(df[date_column])
    end_date = max(df[date_column])

    # get the range of dates in 1 hour increments
    return pd.period_range(
            start=start_date,
            end=end_date,
            freq = "1d"
        ).strftime('%Y-%m-%d')

def get_total_volumes(df):
    '''
    PURPOSE: Total the daily volumes for each ATR
    INPUT: 
        df: dataframe with travel volumes by hour
    OUTPUT:
        dataframe with travel volumes by location by day and travel
        direction. 
    '''
    # Ensure that volumes are integers
    df['Total Volume'] = df['Total Volume'].map(lambda x: x.replace(',', ''))
    df['Total Volume'] = df['Total Volume'].astype('int')
    df.drop(columns = ['Site ID', 'Lane #'], inplace=True)
    return df.groupby([
        "Road", 
        "Device",
        "Location Name",
        "Date",
        "Year", 
        "Weeknum", 
        "Weekday", 
        "Lane Direction" 
    ]).sum().reset_index()

def get_devices(df, col_name):
    '''
    PURPOSE: Get a pandas series of device names
    INPUTS:
        df: dataframe containing the device information
        col_name: column containing device names
    OUTPUT:
        pandas series of device names
    '''
    return pd.Series(df[col_name].value_counts().index.to_list())

def time_table(time_range):
    '''
    PURPOSE: Create an empty dataframe out of a pandas
        period range.
    INPUT:
        time_range: pandas period range
    OUTPUT:
        time_df: pandas dataframe
    '''
    # Create the dataframe
    time_df = pd.DataFrame(
        {
            'Date': time_range
        }
    )
    # Create weeknumber and weekday columns
    time_df['Date'] = pd.to_datetime(time_df['Date'])

    time_df['Weeknum'] = time_df["Date"].dt.isocalendar().week
    time_df["Weekday"] = time_df["Date"].apply(
        lambda x: datetime.datetime.strftime(x, '%A'))

    return time_df

def date_device_tile(devices, time_df, primary_loc_dict, sec_loc_dict):
    '''
    PURPOSE: create a dataframe with rows for each hour in the time
        range, for each device, for all travel directions
    INPUTS:
        devices: pandas series of ATR devices
        time_df: dataframe with one row for every hour in the time interval of
            the COGNOS output
        primary_loc_dict: a dict of device names and primary travel directions
        sec_loc_dict: a dict of device names and secondary travel directions
    OUTPUTS:
        bi_directional_df: a dataframe with a row for every hour for each
            ATR, for each travel direction.
    '''
    # get length variables for np.repeat
    device_count = len(devices)
    time_length = len(time_df)

    # Create two dataframes that have all time intervals for all devices,
    # one for the primary travel direction, and one for the secondary 
    # travel direction.
    primary_df = pd.DataFrame(
            np.repeat(
                time_df.values, 
                device_count, 
                axis=0
            ), 
            columns = time_df.columns, 
            index = np.tile(devices, time_length)
        ).rename_axis("Location Name").reset_index()
    secondary_df = pd.DataFrame(
            np.repeat(
                time_df.values, 
                device_count, 
                axis=0
            ), 
            columns = time_df.columns, 
            index = np.tile(devices, time_length)
        ).rename_axis("Location Name").reset_index()

    df_list = [primary_df, secondary_df]

    print(primary_df.dtypes)
    print(secondary_df.dtypes)

    # Map the travel directions to the devices.
    
    primary_df['Direction'] = primary_df['Location Name'].map(primary_loc_dict)
    secondary_df['Direction'] = secondary_df['Location Name'].map(sec_loc_dict)

    bi_directional_df = pd.concat(
        [
            primary_df,
            secondary_df
        ],
        ignore_index=True
    ).rename(
        columns = {
            'Direction': 'Lane Direction'
        }
    )
    # Sort rows by date and location
    bi_directional_df.sort_values(
        by= [
            'Date',
            'Location Name'
        ],
        inplace=True,
        ignore_index = True
    )
    return bi_directional_df

def map_volumes(bi_directional_df, volumes_df):
    '''
    PURPOSE: Apply the daily volumes calculated in get_total_volumes()
        to the full expanded, bi-directional time df.
    INPUTS: bi_directional_df: the df served by date_device_tile()
            volumes_df: the df served by get_total_volumes()
    OUTPUT:
        final_df: not the final df
    '''
    df = pd.merge(
        bi_directional_df, 
        volumes_df,
        on=[
            "Location Name", 
            "Date", 
            "Weeknum", 
            "Weekday", 
            "Lane Direction"
        ], 
        how="left"
        )
    # Route map to fill in gaps

    road_dict = {
        'I-70 EJMT': "I 70",
        'I-25 Broomfield': "I 25",
        'I-25 Loveland': "I 25",
        'I-25 South of 6th Ave': "I 25",
        'US-50 Pueblo': "US 50",
        'I-225 North of Colfax': "I 225",
        'I-76 Commerce City' : "I 76",
        'I-76 Keenesburg' : "I 76",
        'US-36 Broomfield': "US 36",
        'US-36 Superior': "US 36",
        'US-287 Longmont' : "US 287",
        'US-85 Colorado Springs': "US 85",
        'US-160 Durango': "US 160",
        'US-550 Montrose': "US 550"
        }

    df['Road'] = df['Location Name'].map(road_dict)
    return df


######################################################################################
'''
STEPS

1. Import data
2. Run data_frame_cleaner()
3. Run time_spanner()
4. Use the range from Step 3 to get a time dataframe using time_table()
5. Get total_volumes df with get_total_volumes()
6. Get the device names with get_devices()
7. Tile together the dates for each travel direction of each 
   device with date_device_tile()
8. Get the volume data appended using map_volumes()

'''
# 1.
df = pd.read_csv('ATR_Daily_Report_1-1-19_to_1-3-21.csv')

# 2.
cleaned_df = data_frame_cleaner(df, atr_dict)

# 3.
date_range = time_spanner(cleaned_df, 'Date')

# 4.
time_df = time_table(date_range)

# 5.
total_vol_df = get_total_volumes(cleaned_df)
# total_vol_df.to_csv('total_vol_df.csv')
# 6. 
devices = get_devices(total_vol_df, 'Location Name')

# 7.
frame_df = date_device_tile(devices, time_df, primary_dir_dict, secondary_dir_dict)
# 8.
# This serves up the wrong coumns. I'm getting a Year col and a Site ID col but no volumes column.
frame_df = map_volumes(frame_df, total_vol_df)

#####
frame_df.to_csv('frame_df.csv')