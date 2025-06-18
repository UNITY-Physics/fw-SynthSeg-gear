import flywheel
import json
import pandas as pd
from datetime import datetime
import re
import logging
import os

# Setup basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

#  Module to identify the correct template use for the subject VBM analysis based on age at scan
#  Need to get subject identifiers from inside running container in order to find the correct template from the SDK
def find_gear_version(analyses, filename):
    for asys in analyses:
        for file in asys.files:
            if file.name == filename:
                if 'gambas' in asys.label:
                    return asys.label.split(' ')[0]
                elif 'mrr' in asys.label:
                    return f"{file.gear_info.name}/{file.gear_info.version}"
    return None

def get_demo():

    data = []
    acquisition_cleaned = 'NA'

    # Read config.json file
    p = open('/flywheel/v0/config.json')
    config = json.loads(p.read())

    # Read API key in config file
    api_key = (config['inputs']['api-key']['key'])
    fw = flywheel.Client(api_key=api_key)
    gear = 'synthseg'
    
    # Get the input file id
    input_file_id = (config['inputs']['input']['hierarchy']['id'])
    print("input_file_id is : ", input_file_id)
    input_container = fw.get(input_file_id)

    # Get the session id from the input file id
    # & extract the session container
    session_id = input_container.parents['session']
    session_container = fw.get(session_id)
    session = session_container.reload()
    session_label = session.label
    print("session label: ", session.label)

    # Get the subject id from the session id
    # & extract the subject container
    subject_id = session_container.parents['subject']
    subject_container = fw.get(subject_id)
    subject = subject_container.reload()
    print("subject label: ", session.subject.label)
    subject_label = session.subject.label


    # Specify the directory you want to list files from
    directory_path = '/flywheel/v0/input/input'
    # List all files in the specified directory
    for filename in os.listdir(directory_path):
        if os.path.isfile(os.path.join(directory_path, filename)):
            filename_without_extension = filename.split('.')[0]
            no_white_spaces = filename_without_extension.replace(" ", "")
            no_white_spaces = filename.replace(" ", "")
            acquisition_cleaned = re.sub(r'[^a-zA-Z0-9]', '_', no_white_spaces)
            acquisition_cleaned = acquisition_cleaned.rstrip('_') # remove trailing underscore

            gear_v = find_gear_version(session.analyses, filename)

            if not gear_v:
                for acq in session.acquisitions():
                    acq = acq.reload()
                    gear_v = find_gear_version(acq.analyses, filename)
                    if gear_v:
                        break

    # -------------------  Get the subject age & matching template  -------------------  #

    # get the T2w axi dicom acquisition from the session
    # Should contain the DOB in the dicom header
    # Some projects may have DOB removed, but may have age at scan in the subject container
    age = 'NA'
    sex = 'NA'
    for acq in session_container.acquisitions.iter():
        # print(acq.label)
        acq = acq.reload()

        if 'T2' in acq.label and 'AXI' in acq.label and 'Segmentation' not in acq.label and 'Align' not in acq.label: 
            for file_obj in acq.files: # get the files in the acquisition
                # Screen file object information & download the desired file
                if file_obj['type'] == 'dicom':
                        dicom_header = fw._fw.get_acquisition_file_info(acq.id, file_obj.name)
                        
                        sex = dicom_header.info.get("PatientSex",session.info.get('sex_at_birth', "NA"))
                        dob = dicom_header.info.get('PatientBirthDate', None)
                        series_date = dicom_header.get('SeriesDate', None)
                        scannerSoftwareVersion = dicom_header.info.get('SoftwareVersions', None)
                        
                        if session.info.get('age_at_scan_months', 0) != 0:
                            print("Checking session info for age at scan in months...")
                            age = session.info.get('age_at_scan_months', 0)

                        elif dob != None and series_date != None:
                            # Calculate age at scan
                            # Calculate the difference in months
                            series_dt = datetime.strptime(series_date, '%Y%m%d')
                            dob_dt = datetime.strptime(dob, '%Y%m%d')

                            age = (series_dt.year - dob_dt.year) * 12 + (series_dt.month - dob_dt.month)

                            # Adjust if the day in series_dt is earlier than the day in dob_dt
                            if series_dt.day < dob_dt.day:
                                age -= 1
                        
                        else:
                            print("No DOB in dicom header or age in session info! Trying PatientAge from dicom...")
                            # Need to drop the 'D' from the age and convert to int
                            age = re.sub('\D', '', dicom_header.info.get('PatientAge', "0"))
                           
                        if age <= 0 or age > 1200:  # negative, 0 or 100 years
                            age = 'NA'
                            print("No age at scan - skipping")
                            exit(1)
                    
                        print("Age: ", age)
                        print("Sex: ", sex)
    
    # assign values to lists. 
    data = [{'subject': subject_label, 'session': session_label, 'age': age, 'sex': sex, 'acquisition': acquisition_cleaned, "input_gear_v": gear_v, "scannerSoftwareVersion": scannerSoftwareVersion}]  
    # Creates DataFrame.  
    demo = pd.DataFrame(data)

    filePath = '/flywheel/v0/output/vol.csv'
    with open(filePath) as csv_file:
        vols = pd.read_csv(csv_file, index_col=None, header=0) 
        vols = vols.drop('subject', axis=1)

    frames = [demo, vols]
    df = pd.concat(frames, axis=1)

    out_name = f"{acquisition_cleaned}_synthseg_volumes.csv"
    outdir = ('/flywheel/v0/output/' + out_name)
    df.to_csv(outdir)

    print("Demographics: ", subject_label, session_label, age, sex)
    return subject_label, session_label, age, sex




