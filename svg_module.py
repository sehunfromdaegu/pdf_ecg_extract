#%%
'''
    last updated: 211201
'''
import re
import os
import json
from tqdm import tqdm

def svg_file_paths(directory):
    return [os.path.join(dir,f) for dir, _, files in os.walk(directory) for f in files if f.endswith('.svg')]

def all_tspans(path):
    '''
        returns all tspan elements from given svg file
    '''
    file = open(path, "r")
    tspans = []

    file.seek(0)
    for line in file:
        if 'id="tspan' in line:
            tspans.append(re.split('>|<', line)[1])
            
    return tspans

def parse_age(string):
    if string.endswith(")"): # e.g. '11-MAY-1959 (59 yr)'
        assert(re.split(r"\(|\ |\)", string)[-2] == 'yr')
        age = re.split(r"\(|\ |\)", string)[-3]
    else: # e.g. '63 yr'
        assert(re.split(r"\ ", string)[-1]) == 'yr'
        age = re.split(r"\ ", string)[-2]
    return age

def parse_id(patient_id):
    assert(patient_id[:3] == 'ID:')
    return patient_id[3:]

def parse_gender(gender):
    assert(gender.upper() in {'MALE','FEMALE'})
    return gender.upper()

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

def parse_date(date):
    day, month, year = date.split('-')
    month = parse_month(month)
    return f"{year}-{month}-{day}"

def get_values(path):
    '''
        extracts features from the given svg file and returns them as a dictionary
    '''
    # extract file_name
    assert(path.endswith('.svg'))
    file_name = path.split('/')[-1]

    # skip tspans which are leadnames ('I','II', etc.)
    tspans = all_tspans(path)
    if not tspans[12].startswith('II'):
        # print(f'LEAD II MISSING FOR {path}')
        tspans = tspans[13:]
    else:
        tspans = tspans[14:]
    
    # extract patient_id, date, time
    patient_id, date, time = parse_id(tspans[0]), parse_date(tspans[1].split(' ')[0]), tspans[1].split(' ')[1]

    # extract descriptions(=interpretation) and declare rest of the tspans as 'rest'
    for i in range(len(tspans)):
        if 'mm/s' in tspans[i]:
            interpretation = [{"Diagnosis": d} for d in tspans[3:i]]
            rest = tspans[i:]
            break
    
    # CASE correction: rest[14] should be 'PR interval', but sometimes 'ms' which should be in rest[12] is missing, so that rest[13] becomes 'PR interval'; in this case, we manually add in the missing 'ms'
    if rest[13].startswith('PR'):
        rest = rest[:12] + ['ms'] + rest[12:] # add in missing 'ms' in PR to prevent index shift
    
    assert(rest[11] == 'Vent. rate')
    assert(rest[14] == 'PR interval')
    assert(rest[17] == 'QRS duration')
    assert(rest[19] == 'QT/QTc')
    assert(rest[24] == 'P-R-T axes')

    age, gender = parse_age(rest[25]), parse_gender(rest[26])
    rate, PR, QRSD = rest[10], rest[13], rest[16]
    QT, QTc = rest[20].split("/")
    Paxis, QRSAxis, TAxis = rest[23],rest[22],rest[21]
    
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
        "P Axis": Paxis,
        "QRS Axis": QRSAxis,
        "T Axis": TAxis,
        "interpretation": interpretation
    }
    return feature_dct

def svg_to_json(directory):
    '''
        saves json file next to each svg file contained in the directory
    '''
    for svg_file_path in tqdm(svg_file_paths(directory)):
        try:
            json_file_path = svg_file_path[:-3] + 'json'
            assert(json_file_path.endswith('.json'))

            feature_dct = get_values(svg_file_path)
            with open(json_file_path, 'w') as file:
                json_string = json.dumps(feature_dct)
                file.write(json_string)

        except:
            print(f'failed for {svg_file_path}')

# %%
# directory = '/mount/inf_gatekeeper/Data/Combined_ECGs' # 11703 it
# directory = '/mount/inf_gatekeeper/Data/CONSERVE' # 277 it
# directory = '/mount/inf_gatekeeper/school_data/20200819_complete_data/완전데이터/신촌세브란스_완전데이터' # 3718 it
# directory = './CONSERVE'

# svg_to_json(directory)
# directory = '/home/jmax96/share/inf_gatekeeper/Data/Combined_ECGs'

# for svg_file_path in svg_file_paths(directory):
#     # try:
#     json_file_path = svg_file_path[:-3] + 'json'
#     assert(json_file_path.endswith('.json'))

#     feature_dct = get_values(svg_file_path)
#         # with open(json_file_path, 'w') as file:
#         #     json_string = json.dumps(feature_dct)
#         #     file.write(json_string)

#     # except:
#     #     print(f'failed for {svg_file_path}')
# # %%
