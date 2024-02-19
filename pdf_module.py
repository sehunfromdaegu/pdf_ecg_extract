import re
import fitz
import os
import numpy as np
from parsing import get_svg_data
import scipy.interpolate


def find_newline(str):
    indices = [-1]
    for i in range(len(str)):
        if str[i] == '\n':
            indices.append(i)
    return indices

def split_newline(str):
    list_of_str = []
    indices = find_newline(str)
    for i in range(len(indices)-1):
        begin = indices[i] + 1
        end = indices[i+1]
        list_of_str.append(str[begin:end])

    return list_of_str


def filenames_in(directory):
    '''
        returns filenames(without extension) in directory
    '''
    filelist = os.listdirectory(directory)
    filenames = []

    for file in filelist:
        filename = directory + file.split('.')[0]
        filenames.append(filename)

    filenames = np.asarray(filenames)
    filenames = np.unique(filenames)

    return filenames

def parse_month(month):
    return {
        'JAN': '01',
        'FEB': '02',
        'MAR': '03',
        'APR': '04',
        'MAY': '05',
        'JUN': '06',
        'JUL': '07',
        'AUG': '08',
        'SEP': '09',
        'OCT': '10',
        'NOV': '11',
        'DEC': '12',
    }[month]

def parse_id(list_of_str):
    assert(list_of_str[1][:3] == 'ID:')
    return list_of_str[1][3:]

def parse_date(date):
    day, month, year = date.split('-')
    month = parse_month(month)
    return f"{year}-{month}-{day}"

def parse_age(string):
    if string.endswith(")"): # e.g. '11-MAY-1959 (59 yr)'
        assert(re.split(r"\(|\ |\)", string)[-2] == 'yr')
        age = re.split(r"\(|\ |\)", string)[-3]
    else: # e.g. '63 yr'
        assert(re.split(r"\ ", string)[-1]) == 'yr'
        age = re.split(r"\ ", string)[-2]
    return age

def parse_gender(gender):
    gender = gender.split(' ')[0]
    assert(gender.upper() in {'MALE','FEMALE'})
    return gender.upper()

def get_values_pdf(path):
    '''
    PDF version of function 'get_values' in 'svg_module.py'
    '''
    assert(path.endswith('.pdf'))
    
    missing_lead2 = False 
    doc = fitz.open(path)
    page = doc.load_page(0)
    file_name = path.split('/')[-1]

    # read text
    blocks = page.get_text_blocks()
    subtext = []
    for i in range(len(blocks)):
        subtext.append(blocks[i][4])

    # skip subtext which are leadnames ('I','II', etc.)
    if not subtext[12].startswith('II'):
        # 10s leads 2 are missing in some old pdfs
        print(f'LEAD II MISSING FOR {path}')
        missing_lead2 = True
        subtext = subtext[12:]
    else:
        subtext = subtext[13:]

    # extract patient_id, date, time
    line = split_newline(subtext[0]) # convert a string containing '\n' to several strings
    patient_id = parse_id(line)
    date, _ ,time = line[2].split(' ')
    date = parse_date(date)
    assert(date[4] == '-') # e.g. 2014-05-29
    assert(time[2] == ':') # e.g. 08:54:41

    # extract descriptions and declare rest of the subtext as 'rest'
    for i in range(len(subtext)):
        if 'mm/s' in subtext[i]:
            interpretation = [{"Diagnosis": d[:-1]} for d in subtext[1:i]]
            rest = subtext[i:]
            break

    assert('Vent.' in rest[2])
    assert('PR interval' in rest[3])
    assert('QRS duration' in rest[4])
    assert('QT/QTc' in rest[5])
    assert('P-R-T axes' in rest[6])
    assert('yr' in rest[7])
    assert('ale' in rest[8])

    rate = split_newline(rest[2])[1]
    PR = split_newline(rest[3])[1]
    QRSD = split_newline(rest[4])[1]
    QT, QTc = split_newline(rest[5])[2].split('/')
    TAxis = split_newline(rest[6])[0]
    QRSAxis = split_newline(rest[6])[1]
    PAxis = split_newline(rest[6])[2]
    age = parse_age(split_newline(rest[7])[0])
    gender = parse_gender(split_newline(rest[8])[0])

    feature_dct = {
        "patient_id": patient_id,
        "file_name": file_name,
        "study_date": date,
        "study_time": time,
        "gender": gender,
        "age": age,
        "Heart rate": rate,
        "PR Interval": PR,
        "QRS Interval": QRSD,
        "QT Interval": QT,
        "QTc Interval": QTc,
        "P Axis": PAxis,
        "QRS Axis": QRSAxis,
        "T Axis": TAxis,
        "interpretation": interpretation
    }

    return feature_dct, missing_lead2

def read_waves_pdf(filename):
    doc = fitz.open(filename)
    page = doc.load_page(0)
    svg = page.get_svg_image(matrix=fitz.Identity, text_as_path=False)
    wave, freq = get_svg_data('S', svg)

    return wave, freq

def upsampling(wave, factor=2):
    x = np.arange(0,len(wave), 1)
    f = scipy.interpolate.interp1d(x,wave, fill_value='extrapolate', kind='quadratic')
    xnew = np.arange(0,len(wave),1/factor)
    return f(xnew) 

def waves_and_features(directory):
    '''
    input : directory that contains n-pdfs 
    output : list of waves, features of length n 
    '''
    filenames = filenames_in(directory)
    waves, features = [], []

    # read pdf files
    for filename in filenames:
        pdf = filename + '.pdf'
        # extract features
        feature_dct, missing_lead2 = get_values_pdf(pdf)
        
        # pass the case when pdf does not contain 10s lead 2
        if not missing_lead2:
            # read wave
            wave, freq = read_waves_pdf(pdf)
            
            # when freq is 250Hz, we upsample to 500Hz
            if freq == 250:
                for i in range(13):
                    wave[i] = upsampling(wave[i], factor=2)

            waves.append(wave)
            features.append(feature_dct)

    return waves, features