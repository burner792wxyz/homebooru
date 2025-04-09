import re

special_charecters = re.compile(r'[~!@#$%^&*()_+{}":;\'-+=<>,.?/|]')

def lev_distance(str1: str, str2: str) -> float:#get minimum number of edits to change str1 to str2
    global calls, stored_lev_distances
    try:
        dist = None
        if (str1, str2) in stored_lev_distances.keys():
           dist = stored_lev_distances.get((str1, str2))
        elif (str2, str1) in stored_lev_distances.keys():
           dist = stored_lev_distances.get((str2, str1))
        if dist != None: return dist
    except NameError:
        stored_lev_distances = {}

    len1 = len(str1)
    len2 = len(str2)

    #empty case
    if len1 == 0 or len2 == 0:
        dist = max(len1, len2)
        stored_lev_distances.update({(str1, str2): dist})
        return dist
    
    #construct tails
    tail1 = str1[1:]
    tail2 = str2[1:]

    #matching head case
    if str1[0] == str2[0]:
        dist = lev_distance(tail1, tail2)
        stored_lev_distances.update({(str1, str2): dist})
        return dist
    
    #matching tail case
    if tail1 == tail2:
        dist = 1
        stored_lev_distances.update({(str1, str2): dist})
        return dist
    #final case
    tail1_case = lev_distance(tail1, str2)
    tail2_case = lev_distance(str1, tail2)
    tail_both_case = lev_distance(tail1, tail2)
    #print(f'lev_distance({str1}, {str2})')
    #print(f'tail1_case: {tail1_case}\n tail2_case: {tail2_case}\n tail_both_case: {tail_both_case}\n')
    dist = 1 + min(tail1_case, tail2_case, tail_both_case)
    stored_lev_distances.update({(str1, str2): dist})
    return dist

    raise Exception('lev_distance failed')

def lev_similarity(str1: str, str2: str) -> float:
    return 1 - (lev_distance(str1, str2) / (max(len(str1), len(str2))))

def check_spesific_key(key, value) -> bool:
    #print(f'checking {key} in {value}')
    if re.search(special_charecters, key) != None:
        if '~' in key:
            dist = lev_similarity(key, value)
            if dist < 0.55:
                return False
            else:
                #print(f'lev_similarity({key}, {value}): {dist}')
                return True
            
        elif '*' in key:
            key = key.replace('*', '.*')
            match = re.match(key, value)
            if match != None:
                return True
            else:
                return False
            
        elif '-' in key:
            key = key.replace('-', '')
            if key in value:
                return False
            else:
                return True
            
        else:
            if key in value:
                return True
            else:
                return False
    else:
        if key == value:
            return True
            
    return False

def is_value_in_post_key(post_data, key, value):
    #print(f'checking {key}:{value} in {post_data[key]}')
    if type(post_data[key]) == list:
        for item in post_data[key]:
            if check_spesific_key(value, item):
                return True
        return False
    else:
        if check_spesific_key(value, post_data[key]):
            return True
        else:
            return False

def post_checker(post_data : dict, requirments: dict) -> bool:
    if 'mediadata' in post_data.keys():
        media_keys = post_data['mediadata'].keys()
    else:
        media_keys = []
    for item in requirments.items():
        key = item[0]
        value = item[1]
        if type(value) == str:
            value_list = [value]
        else:
            value_list = value

        for value in value_list:
            if key in media_keys:
                post_data = post_data['mediadata']
            elif key not in post_data.keys():
                print(f'{key} not in post_data')
                return False
            req_fulfilled = is_value_in_post_key(post_data, key, value)
            if req_fulfilled == False:
                return False
            #print(f'{value} in {post_data[key]} : {req_fulfilled}')

        #print(f'checked list: {checked_list} \n')
    return True
