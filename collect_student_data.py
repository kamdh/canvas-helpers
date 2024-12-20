#!/usr/bin/python3

import pandas as pd
import os
import glob
import numpy as np
from shutil import copy2

grades_file = "2024-12-16T2339_Grades-CSCI_405.csv"
directory = "./CSCI405_1760059"
dest_dir = "Student_Work"
num_picks = 3
np.random.seed(100)

grades = pd.read_csv(grades_file)
grades = grades.drop([0,1]) # 0 = "Manual posting" etc., 1 = "Points possible"
grades = grades.set_index(np.arange(grades.shape[0])) # reindex from student 0

sub_dirs = glob.glob(f"{directory}/*")

def copy_files(assignment_dir, dest_dir, student_ids, prefix_str):
    for student in student_ids:
        # assumption: filenames are "user@wwu.edu.pdf"
        submission = f"{student}.pdf"
        src_file = f"{assignment_dir}/{submission}"
        dest_file = f"{dest_dir}/{prefix_str}_{submission}"
        print(f"copying {src_file} to {dest_file}")
        try:
            copy2(src_file, dest_file)
        except FileNotFoundError:
            print("== Warning, file {src_file} missing! ==")

def clean_str(str):
    return str.replace(' ', '_').replace('(', '').replace(')', '')

for sub_dir in sub_dirs:
    assignment_id = sub_dir.split('/')[-1]
    column = grades.filter(regex=assignment_id, axis=1).astype(float)
    if column.shape[1] == 0:
        print(f"Warning, no column found in {grades_file} for id {assignment_id}")
    elif column.shape[1] > 1:
        print(f"Error, more than 1 column found in {grades_file} for id {assignment_id}")
    else:
        col_data = np.array(column).flatten() # may include NaN for missing

        if np.all(np.logical_or(col_data == 0, np.isnan(col_data))):
            print(f"Warning, skipping columns \"{column.columns[0]}\"")
            continue

        bins = np.nanquantile(col_data, [0.1, 0.5, 0.75, 1], method="inverted_cdf")
        # find bins for poor/middle/good scores
        low_idx = (col_data >= bins[0]) * (col_data < bins[1])
        mid_idx = (col_data >= bins[1]) * (col_data < bins[2])
        top_idx = (col_data >= bins[2]) * (col_data <= bins[3])
        # indices of students in bisn
        low_students = np.random.choice(np.where(low_idx)[0], num_picks, replace=False)
        mid_students = np.random.choice(np.where(mid_idx)[0], num_picks, replace=False)
        top_students = np.random.choice(np.where(top_idx)[0], num_picks, replace=False)
        # list of student emails
        low_emails = list(grades['SIS Login ID'].iloc[low_students])
        mid_emails = list(grades['SIS Login ID'].iloc[mid_students])
        top_emails = list(grades['SIS Login ID'].iloc[top_students])

        prefix_str = clean_str(column.columns[0])
        copy_files(sub_dir, f"{dest_dir}/Poor", low_emails, prefix_str)
        copy_files(sub_dir, f"{dest_dir}/Average", mid_emails, prefix_str)
        copy_files(sub_dir, f"{dest_dir}/Good", top_emails, prefix_str)
        
        #break
