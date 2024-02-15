'''
Wave extraction script from .svg files
- original file: parsing.py written by Taejin
- since older ecg files (like ones before 2007) had 250Hz frequencies, I have made manual changes to the script
    - each change can be searched with "# CORRECTION"
    - the corrections are made only to work with mode = 'S' (Severance), so using this script for extracting HY type ecg files will not work
'''
import numpy as np
import xml.etree.ElementTree as ET

def parse_path(pathdef, current_pos=0 + 0j):
    verts = []
    for c, v in _parse_path(pathdef, current_pos):
        verts.append(list(v[0]))
    return np.array(verts)


def _parse_path(pathdef, current_pos):
    COMMANDS = set('MmZzLlHhVvCcSsQqTtAa')
    UPPERCASE = set('MZLHVCSQTA')
    COMMAND_CODES = {
        'M': (1,),
        'L': (2,),
        'H': (2,),
        'V': (2,),
        'Q': (3, 3),
        'T': (3, 3),
        'C': (4, 4, 4),
        'S': (4, 4, 4),
        'Z': (79,),
        'A': None
    }

    def _next_pos(elements):
        return float(elements.pop()) + float(elements.pop()) * 1j

    elements = ','.join(pathdef.strip().split(' ')).split(',')
    elements.reverse()

    start_pos = None
    command = None

    while elements:

        if elements[-1] in COMMANDS:
            last_command = command
            command = elements.pop()
            absolute = command in UPPERCASE
            command = command.upper()
        else:
            if command is None:
                raise ValueError(
                    "Unallowed implicit command in {}, position {}".format(
                        pathdef, len(pathdef.split()) - len(elements)))
            last_command = command

        if command == 'M':
            pos = _next_pos(elements)
            if absolute:
                current_pos = pos
            else:
                current_pos += pos
            start_pos = current_pos

            yield COMMAND_CODES['M'], [(current_pos.real, current_pos.imag)]

            command = 'L'

        elif command == 'Z':
            if current_pos != start_pos:
                verts = [(start_pos.real, start_pos.imag)]
                yield COMMAND_CODES['L'], verts

            verts = [(start_pos.real, start_pos.imag)]
            yield COMMAND_CODES['Z'], verts

            current_pos = start_pos
            start_pos = None
            command = None

        elif command == 'L':
            pos = _next_pos(elements)
            if not absolute:
                pos += current_pos
            verts = [(pos.real, pos.imag)]
            yield COMMAND_CODES['L'], verts
            current_pos = pos

        elif command == 'H':
            x = elements.pop()
            pos = float(x) + current_pos.imag * 1j
            if not absolute:
                pos += current_pos.real
            verts = [(pos.real, pos.imag)]
            yield COMMAND_CODES['H'], verts
            current_pos = pos

        elif command == 'V':
            y = elements.pop()
            pos = current_pos.real + float(y) * 1j
            if not absolute:
                pos += current_pos.imag * 1j
            verts = [(pos.real, pos.imag)]
            yield COMMAND_CODES['V'], verts
            current_pos = pos

        elif command == 'C':
            control1 = _next_pos(elements)
            control2 = _next_pos(elements)
            end = _next_pos(elements)
            if not absolute:
                control1 += current_pos
                control2 += current_pos
                end += current_pos
            verts = [
                (control1.real, control1.imag),
                (control2.real, control2.imag),
                (end.real, end.imag)
            ]
            yield COMMAND_CODES['C'], verts
            current_pos = end

        elif command == 'S':
            if last_command not in 'CS':
                control1 = current_pos
            else:
                last_control = control2
                control1 = current_pos + current_pos - last_control
            control2 = _next_pos(elements)
            end = _next_pos(elements)
            if not absolute:
                control2 += current_pos
                end += current_pos
            verts = [
                (control1.real, control1.imag),
                (control2.real, control2.imag),
                (end.real, end.imag)
            ]
            yield COMMAND_CODES['S'], verts
            current_pos = end

        elif command == 'Q':
            control = _next_pos(elements)
            end = _next_pos(elements)
            if not absolute:
                control += current_pos
                end += current_pos
            verts = [
                (control.real, control.imag),
                (end.real, end.imag)
            ]
            yield COMMAND_CODES['Q'], verts
            current_pos = end

        elif command == 'T':
            if last_command not in 'QT':
                control = current_pos
            else:
                last_control = control
                control = current_pos + current_pos - last_control
            end = _next_pos(elements)
            if not absolute:
                end += current_pos
            verts = [
                (control.real, control.imag),
                (end.real, end.imag)
            ]
            yield COMMAND_CODES['T'], verts
            current_pos = end
            
def get_attrib(file_name):
    tree = ET.parse(file_name)
    result = []
    for el in tree.iter():
        if el.tag[-4:] == 'path':
            result.append(el)

    result2 = []
    for el in result:
        result2.append(
            el.attrib['d']
        )
    return result2

def get_attrib_string(str):
    tree = ET.fromstring(str)
    result = []
    for el in tree.iter():
        if el.tag[-4:] == 'path':
            result.append(el)

    result2 = []
    for el in result:
        result2.append(
            el.attrib['d']
        )
    return result2


def get_svg_data(mode, file_name):
    if mode != 'H' and mode != 'S':
        print('H or S only')
        return

    if mode == 'H':
        NUM_BASE = 8
        VALID_LENGTHS = [1247, 1250, 4997]
        FIRST_COLUMN_NUM = 1247
        REMAINED_NUM = 1250
        LAST_NUM = 4997
        DEFAULT_GAP = 82
    else:
        NUM_BASE = 60
        VALID_LENGTHS = [619, 2500, 1238, 5000] # CORRECTION: ADDED 619, 2500 to handle waves with 250Hz frequency
        FIRST_COLUMN_NUM = 1238
        REMAINED_NUM = 1238
        LAST_NUM = 5000
        DEFAULT_GAP = 1000
        
        # CORRECTION: ADDED below three lines to handle waves with 250Hz frequency
        FIRST_COLUMN_NUM_250 = 619
        REMAINED_NUM_250 = 619
        LAST_NUM_250 = 2500

    def get_base(arrays):
        _result = []
        for _el in arrays:
            if len(_el) == NUM_BASE:
                assert np.max(_el[:, 1]) - _el[0][1] == DEFAULT_GAP
                _result.append(_el[0][1])
        return _result

    def get_data(arrays):
        _result = []
        for _el in arrays:
            if len(_el) in VALID_LENGTHS:
                _result.append(_el)
                
        return _result

    attribs = []
    if file_name[0] == '<': # We implicity assume that svg string starts with '<'
        attribs = get_attrib_string(file_name)
    else:
        attribs = get_attrib(file_name)

    result = []
    for el in attribs:
        result.append(
            parse_path(el)
        )

    base = get_base(result)
    list_of_arrays = get_data(result)
    assert len(base) == 4
    assert len(list_of_arrays) == 13

    # CORRECTION: ADDED below assert statement
    assert np.all([list_of_arrays[j].shape[0] == list_of_arrays[0].shape[0] for j in range(12)]) 

    # CORRECTION: ADDED below if-elif-else statement to initiate FREQ variable
    if list_of_arrays[0].shape[0] == 1238:
        assert list_of_arrays[12].shape[0] == 5000
        FREQ = 500
        
    elif list_of_arrays[0].shape[0] == 619:
        assert list_of_arrays[12].shape[0] == 2500
        FREQ = 250
        
    else:
        assert(False)


    base.sort(reverse=True)
    list_of_arrays.sort(reverse=True, key=lambda x: np.median(x[:, 1]))

    first_row = list_of_arrays[:4]
    second_row = list_of_arrays[4:8]
    third_row = list_of_arrays[8:12]
    last_row = list_of_arrays[-1]
    first_row.sort(key=lambda x: x[0][0])
    second_row.sort(key=lambda x: x[0][0])
    third_row.sort(key=lambda x: x[0][0])

    # CORRECTION: ADDED if-else statement to handle waves with 250Hz frequency
    # originally the if statement body was all that existed
    if FREQ == 500:
        wave_1 = first_row[0] - np.array([[0, base[0]]] * FIRST_COLUMN_NUM)
        wave_aVR = first_row[1] - np.array([[0, base[0]]] * REMAINED_NUM)
        wave_V1 = first_row[2] - np.array([[0, base[0]]] * REMAINED_NUM)
        wave_V4 = first_row[3] - np.array([[0, base[0]]] * REMAINED_NUM)

        wave_2 = second_row[0] - np.array([[0, base[1]]] * FIRST_COLUMN_NUM)
        wave_aVL = second_row[1] - np.array([[0, base[1]]] * REMAINED_NUM)
        wave_V2 = second_row[2] - np.array([[0, base[1]]] * REMAINED_NUM)
        wave_V5 = second_row[3] - np.array([[0, base[1]]] * REMAINED_NUM)

        wave_3 = third_row[0] - np.array([[0, base[2]]] * FIRST_COLUMN_NUM)
        wave_aVF = third_row[1] - np.array([[0, base[2]]] * REMAINED_NUM)
        wave_V3 = third_row[2] - np.array([[0, base[2]]] * REMAINED_NUM)
        wave_V6 = third_row[3] - np.array([[0, base[2]]] * REMAINED_NUM)

        wave_2_whole = last_row - np.array([[0, base[3]]] * LAST_NUM)
        
    else: 
        assert(FREQ == 250)

        wave_1 = first_row[0] - np.array([[0, base[0]]] * FIRST_COLUMN_NUM_250)
        wave_aVR = first_row[1] - np.array([[0, base[0]]] * REMAINED_NUM_250)
        wave_V1 = first_row[2] - np.array([[0, base[0]]] * REMAINED_NUM_250)
        wave_V4 = first_row[3] - np.array([[0, base[0]]] * REMAINED_NUM_250)

        wave_2 = second_row[0] - np.array([[0, base[1]]] * FIRST_COLUMN_NUM_250)
        wave_aVL = second_row[1] - np.array([[0, base[1]]] * REMAINED_NUM_250)
        wave_V2 = second_row[2] - np.array([[0, base[1]]] * REMAINED_NUM_250)
        wave_V5 = second_row[3] - np.array([[0, base[1]]] * REMAINED_NUM_250)

        wave_3 = third_row[0] - np.array([[0, base[2]]] * FIRST_COLUMN_NUM_250)
        wave_aVF = third_row[1] - np.array([[0, base[2]]] * REMAINED_NUM_250)
        wave_V3 = third_row[2] - np.array([[0, base[2]]] * REMAINED_NUM_250)
        wave_V6 = third_row[3] - np.array([[0, base[2]]] * REMAINED_NUM_250)

        wave_2_whole = last_row - np.array([[0, base[3]]] * LAST_NUM_250)
        
    # CORRECTION: Added FREQ to be a return variable
    # CORRECTION: changed so that only the y-values were returned
    return [
        wave_2_whole[:,1],
        wave_1[:,1],
        wave_2[:,1],
        wave_3[:,1],
        wave_aVR[:,1],
        wave_aVL[:,1],
        wave_aVF[:,1],
        wave_V1[:,1],
        wave_V2[:,1],
        wave_V3[:,1],
        wave_V4[:,1],
        wave_V5[:,1],
        wave_V6[:,1],
    ], FREQ