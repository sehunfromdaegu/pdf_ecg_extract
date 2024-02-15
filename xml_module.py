'''
    Below is the module used for SNUBH wave extraction in Feburary 2022.
    - original code: share/inf/workspace_philip/generators/210207_ecg_xml_extraction.py
    - made a few changes (marked with #CHANGE)
'''

import numpy as np
import base64
import xml.etree.ElementTree as et

def bytearray_to_bitarray(bytesarray):
    output = []
    for byte in bytesarray:
        output += [
            (byte & 2 ** 7) >> 7,
            (byte & 2 ** 6) >> 6,
            (byte & 2 ** 5) >> 5,
            (byte & 2 ** 4) >> 4,
            (byte & 2 ** 3) >> 3,
            (byte & 2 ** 2) >> 2,
            (byte & 2 ** 1) >> 1, 
            (byte & 2 ** 0) >> 0,
        ]
    return output

def bitarray_to_intarray(bitarray, nr=8):
    

    remainder = len(bitarray) % nr
    bits = bitarray
#     if remainder != 0 :
#         bits += (nr - remainder) * [0]
        
    output = [
        int(''.join([str(i) for i in bits[nr*idx:nr*(idx+1)]]), 2)
        for idx in range(len(bits) // nr)
    ]
        
    return output

# LZW decompressor for 'parsedwaveforms' in .xml file
def LZW_decompress(compressed, dictionary_size=256):
    
    dict_size = dictionary_size
    dictionary = {chr(i): chr(i) for i in range(dict_size)}
    old = result = compressed[0]
    ch = old
    for new in compressed[1:]:
        if ord(new) == dict_size:
#             print("X", end='')
            string = old
            string = string + ch
        elif ord(new) < dict_size:
#             print("O", end='')
            string = dictionary[new]
        else:
            raise ValueError
        
#         print("STRING:", string)
        result += string
        
        ch = string[0]
        dictionary[chr(dict_size)] = old + ch
        dict_size += 1
        old = dictionary[new]       
#     print(result)
    return [ord(item) for item in result]

def delta_decompression(deltas, first):

    x = deltas[0]
    y = deltas[1]
    output = [x, y]
    delta_code = first
    
    for idx in range(2, 5500):
        z = ((y + y) - x - delta_code)
        delta_code = deltas[idx] - np.int16(64)
        output.append(z)
        x = y
        y = z
        
    return output

def XLI_decode(compressed_b64):
        
    output = []
    
    # decode base64
    compressed_bytes = base64.b64decode(compressed_b64)
    
#     print("compsize", len(compressed_bytes))
    while len(compressed_bytes) != 0:
        header = compressed_bytes[:8]
        data_size = np.frombuffer(header[:4], dtype=np.int32)[0]
        mystery_number = np.frombuffer(header[4:6], dtype=np.int16)[0]
        delta_code = np.frombuffer(header[6:], dtype=np.int16)[0]
        
        chunk = compressed_bytes[8:data_size+8]
        compressed_bytes = compressed_bytes[data_size+8:]
#         print('delta:', delta_code, header[6:])
#         print("Lengths:", len(chunk), len(compressed_bytes))

        bitarray = bytearray_to_bitarray(chunk)
        byte10_array = bitarray_to_intarray(bitarray, 10)
        
        cut_idx = 0
        decomp = 11111 * [0]
        
        while len(decomp)!=11000: 
            try:
                decomp = LZW_decompress([chr(i) for i in byte10_array[:len(byte10_array)-cut_idx]], 256)
                if len(decomp) != 11000:
                    raise ValueError
            except:
                cut_idx += 1
                if len(decomp) < 11000:
                    print(len(decomp))
                    raise ValueError
        
        # unroll delta
        unrolled_delta = []
        for idx in range(5500):
            unrolled_delta.append(
                np.frombuffer(
                    bytearray([decomp[5500+idx], decomp[idx]]), dtype=np.int16
                )[0]
            ) 
        
        # decode delta
        unrolled_delta = delta_decompression(unrolled_delta, delta_code)
            
        output.append(np.array(unrolled_delta, dtype='float64'))
        
    # Lead Order : I, II, III, aVR, aVL, aVF, V1, V2, V3, V4, V5, V6
    # Length of 'output' = 16
    # i.e. last 4 waves of output are empty 
    # (maybe there are slots for 16 leads case)
    
    # correction for lead III, aVR, aVL, aVF 
    output[2] = output[1] - output[0] - output[2]  # lead III
    output[3] = -output[3] - (output[0] + output[1])/2 # lead aVR
    output[4] = (output[0] - output[2])/2 - output[4] # lead aVL
    output[5] = (output[1] + output[2])/2 - output[5] # lead aVF
    
    return output
    
def waves_from_xml_file_SNUB(xml_path):
    xmlns = 'http://www3.medical.philips.com'
    xml = et.parse(xml_path)
    '''
        #CHANGE: changed code for finding wave_node (three lines of code below)
        xml structure: (arrow denotes child element)
            root -> waveforms -> parsedwaveforms
    '''
    root = xml.getroot() 
    waveforms = root.findall('{' + xmlns + '}' + 'waveforms')[-1]
    wave_node = waveforms.findall('{' + xmlns + '}' + 'parsedwaveforms')[-1]

    # Check whether wave_node is a right node for waves
    assert(wave_node.tag.split('}')[-1] == 'parsedwaveforms') #CHANGE: changed if statement with raise error to assert statement

    return XLI_decode(wave_node.text)[:12]