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

names_dict = {
                "070E214 I-70 E/B JOHNSON / EISENHOWER TUNNEL": "I-70 EJMT",
                "070W216 I-70 W/B EISENHOWER / JOHNSON TUNNEL": "I-70 EJMT",
                
                "225N011 SH 225 S/O I-70 - N/O COLFAX": "I-225 North of Colfax",
                "025N209 I-25 S/O 6TH AVE. N/B ( DENVER )": "I-25 South of 6th Ave",
                "025N209 I-25 S/O 6TH AVE. S/B ( DENVER )": "I-25 South of 6th Ave",
                
                "025N230 I-25 N/O SH 7 INTERCHANGE": "I-25 Broomfield",
                
                # Possibly try to map the new device names to I-25 Loveland as well
                "000N256 I-25 S/O SH 34 INTERCHANGE (LOVELAND)": "I-25 Loveland",
                
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

def data_frame_cleaner(df, atr_dict):
    '''
        Purpose: read in COGNOS ATR Report and reformat it.
        I
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

    df["Weeknum"] = df["Date"].dt.week

    df["Weekday"] = df["Date"].apply(
        lambda x: datetime.datetime.strftime(x, '%A')
        )

    df["Year"] = df["Date"].dt.year

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
    
    start_date = min(df.date_column)
    end_date = max(df.date_column)

    time_interval = pd.period_range(
        start=start_date,
        end=end_date,
        freq = "1d"
    ).strftime('%Y-%m-%d')
    