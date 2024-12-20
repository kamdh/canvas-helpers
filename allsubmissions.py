#!/usr/bin/python3
"""Canvas allows bulk assignment submission downloading, but does not provide any control over file naming. This
script downloads an assignment's submissions and names them according to the submitter's Login ID (typically their
institutional student number) or group name."""

__author__ = 'Kameron Decker Harris'
__copyright__ = 'Copyright (c) Kameron Decker Harris'
__license__ = 'Apache 2.0'
__version__ = '2024-12-19'  # ISO 8601 (YYYY-MM-DD)

import argparse
import concurrent.futures
import csv
import datetime
import functools
import json
import os
import re
import sys
import time

import subprocess

import openpyxl.utils
import requests

from canvashelpers import Args, Config, Utils


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs=1,
                        help='Please provide the URL of the coursse to download submissions for.')
    parser.add_argument('--working-directory', default=None,
                        help='The location to use for output (which will be created if it does not exist). Default: the same directory as this script')
    parser.add_argument('--speedgrader-file', default=None, choices=['XLSX', 'CSV'], type=str.upper,
                        help='Set this option to `XLSX` or `CSV` to create a file in the specified format containing '
                             'students\' (or groups\') names, IDs (both Canvas and institutional) and a link to the '
                             'SpeedGrader page for the assignment, which is useful when marking activities such as '
                             'presentations or ad hoc tasks. If present, Turnitin report links are also included. No '
                             'assignment attachments are downloaded in this mode')
    parser.add_argument('--turnitin-pdf-session-id', default=None,
                        help='If needed, it is also possible to generate and download Turnitin similarity report PDFs '
                             'instead of the original assignment submissions. To do this, first visit any Turnitin '
                             'report page, then open your web browser\'s JavaScript console and enter'
                             '`Object.fromEntries([document.cookie].map(v=>v.split(/=(.*)/s)))["legacy-session-id"]` '
                             '(without quotes). Pass the resulting value (without quotes) using this parameter. None '
                             'of the original assignment attachments are downloaded in this mode')
    parser.add_argument('--submitter-pattern', default=None,
                        help='Use this option to pass a (case-insensitive) regular expression pattern that will be '
                             'used to filter and select only submitters whose names *or* student numbers match. For '
                             'example, `^Matt(?:hew)?\\w*` will match only students whose first name is `Matt` or '
                             '`Matthew`, whereas `^123\\d{3}$` will match six–digit student numbers starting with '
                             '`123`. In groups mode this pattern is used to match *group names* only')
    parser.add_argument('--multiple-attachments', action='store_true',
                        help='Use this option if there are multiple assignment attachments per student or group. This '
                             'will change the behaviour of the script so that a new subfolder is created for each '
                             'submission, named as the student\'s number or the group\'s name. The original filename '
                             'will be used for each attachment that is downloaded. Without this option, any additional '
                             'attachments will be ignored, and only the first file found will be downloaded')
    return parser.parse_args()

args = Args.interactive(get_args)
COURSE_URL = Utils.course_url_to_api(args.url[0])
COURSE_ID = Utils.get_assignment_id(COURSE_URL)  # used only for output directory
print(f"Retrieving data for {COURSE_ID}")
working_directory = os.path.dirname(
    os.path.realpath(__file__)) if args.working_directory is None else args.working_directory
print(f"Working dir: {working_directory}")
os.makedirs(working_directory, exist_ok=True)
OUTPUT_DIRECTORY = '%s/%d' % (working_directory, COURSE_ID)
print(f"Output dir: {OUTPUT_DIRECTORY}")
if os.path.exists(OUTPUT_DIRECTORY):
    print('ERROR: assignment output directory', OUTPUT_DIRECTORY, 'already exists - please remove or rename')
    sys.exit()
os.mkdir(OUTPUT_DIRECTORY)


assignment_details_response = requests.get(COURSE_URL, headers=Utils.canvas_api_headers())
if assignment_details_response.status_code != 200:
    print('ERROR: unable to get course details - did you set a valid Canvas API token in %s?' % Config.FILE_PATH)
    sys.exit()

#GROUPS = ["hw", "quiz", "exam"]
GROUPS = ["hw", "labs", "project"]

## Find assignment group ids to keep
assignments_response = Utils.canvas_multi_page_request(f"{COURSE_URL}/assignment_groups", type_hint="assignments list")
assignments_json = json.loads(assignments_response)
group_ids = []
for assignment in assignments_json:
    if assignment['name'] in GROUPS:
        group_ids.append(assignment['id'])
        print(f"id: {assignment['id']}, name: {assignment['name']}")
print(group_ids)

## Fetch all assignments and keep ones from selected group ids
assignments_response = Utils.canvas_multi_page_request(f"{COURSE_URL}/assignments", type_hint="assignments list")
assignments_json = json.loads(assignments_response)
assignment_ids = []
assignment_dict = []
for assignment in assignments_json:
    if assignment['assignment_group_id'] in group_ids:
        assignment_ids.append(assignment['id'])
        print(f"id: {assignment['id']}, name: {assignment['name']}")
print(assignment_ids)

## Now call the submission downloader for each assignment
for assignment in assignment_ids:
    ASSIGNMENT_URL = f"{args.url[0]}/assignments/{assignment}"
    cmd_str = f"python3 submissiondownloader.py {ASSIGNMENT_URL} --working-directory {OUTPUT_DIRECTORY} --multiple-attachments"
    print(f"running '{cmd_str}'")
    os.system(cmd_str)
