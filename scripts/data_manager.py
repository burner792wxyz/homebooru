'''
create folders and shii
'''
import os, orjson, asyncio, tqdm # type: ignore
from PIL import Image

#json handling
def read_json(filepath: str, no_error = False):
    try:
        with open(filepath, 'r', encoding='UTF-8') as file_obj:
            file_text = file_obj.read()
            if len(file_text) == 0: return None
            result = dict(orjson.loads(file_text))
    except Exception as Ex:
        if no_error:
            print(Ex)
            return None
        else: 
            raise Ex
    return(result)

def write_json(filepath: str, obj: dict) -> None:
    if obj in [None, '']:
        print(f'failed to write to {filepath} while creating post because invalid object was given \n {__name__} \n')
    with open(filepath, 'wb') as file_obj:
        json_bytes = orjson.dumps(obj)
        file_obj.write(json_bytes)


#create things
def create_file(filepath: str, data: bytes, mode = 'a' ) -> bool:
    '''mode: w = overwrite, j = json. multiple modes can be used together
    
    '''
    path, filename = os.path.split(filepath)
    if 'w' in mode and os.path.isfile(filepath):
        os.remove(filepath)
    if filename not in os.listdir(path):
        print(f'file: {filepath} not found, creating')
        if 'j' in mode:
            write_json(filepath, data)
            return True
        else:
            with open(filepath, mode, encoding="utf-8") as file:
                file.write(data)
                return True
    return False

def create_folder(filepath: str) -> bool:
    try:
        os.makedirs(filepath)
        return True
    except FileExistsError:
        return False

def create_site(site: str):
    global dataset_path
    site_path = f'{dataset_path}/{site}'
    stats_changed()
    create_folder(f'{site_path}/media')
    
    tag_data = {'description': 'dictionary of posts'}
    create_file(f'{site_path}/post_data.json', tag_data, mode='j')
    master_list = read_json(f'{dataset_path}/master_list.json')
    master_list.update({site : [0]})    
    write_json(f'{dataset_path}/master_list.json', master_list)

def create_post(post):
    '''adds post to: 
    site/post_data.json, master_list.json, tag_dict.json'''

    stats_changed()
    #add to post data
    sites = [x for x in os.listdir(dataset_path) if os.path.isdir(f'{dataset_path}/{x}')]
    if not post.site in sites:
        create_site(post.site)
    if post.data_path == None:
        post.data_path == f'{dataset_path}/{post.site}/post_data.json'
    post_data_file = read_json(post.data_path)
    post_data_file.update({post.num_id : post.data_dictionary})
    write_json(post.data_path, post_data_file)
    #add to master list
    master_list_path = f'{dataset_path}/master_list.json'
    full_list = read_json(master_list_path)
    if post.site in full_list.keys(): 
        full_list[post.site].append(post.num_id)
    else: 
        full_list.update({post.site : post.num_id})

    if 'master' in full_list.keys():
        full_list["active"].append(post.id)
    else:
        full_list.update({'master' : post.id})  
    write_json(master_list_path, full_list)


def create_all():
    global prefix, dataset_path
    print(f'called create_all in datamanager from {__name__} {__file__}')
    create_folder(f'{prefix}/static/temp/media')
    create_folder(f'{dataset_path}')

    create_file(f'{dataset_path}/master_list.json', classes.master_list.starter_dict, mode='ja')
    create_file(f'{dataset_path}/tag_dict.json', classes.tag_dict.starter_dict, mode='ja')
    #create_file(f'{prefix}/static/temp/cache.json', {"stored_search" : {"search" : "", "ids" : [], 'start_page' : 0}}, mode='jw')
    create_file(f'{dataset_path}/stats.json', classes.stats.start_dict, mode='j')

    create_site('homebooru')

    if stats_invalid():
        update_stats()

#delete things
def delete_post(post_name: str) -> bool:
    global dataset_path
    stats_changed()
    post_site, post_id = post_name.split('_')

    #delete from site data list
    data_path = f'{dataset_path}/{post_site}/post_data.json'
    all_post_data = read_json(data_path)
    if str(post_id) in all_post_data.keys():
        del all_post_data[str(post_id)]
        write_json(data_path, all_post_data)
        print(f'succesfully deleted {post_name} from {data_path}')
    else:
        #error = True
        #print(list(all_post_data)[0:20])
        print(f'{post_id} is not present in {data_path} ; could not delete')

    #delete from master list
    master_list_path = f'{dataset_path}/master_list.json'
    master_list = read_json(master_list_path)
    if str(post_name) in master_list["active"]:
        master_index = master_list["active"].index(str(post_name))
        del master_list["active"][master_index]
        print(f'succesfully deleted {post_name} from master_list["active"][master_index]')
    else: 
        #print(list(master_list["active"])[0:20])
        print(f'{post_name} is not present in master_list["active"][master_index] ; could not delete')
    
    #add to deleted posts
    if not 'deleted' in master_list.keys():
        master_list.update({'deleted':[]})
    master_list['deleted'].append(post_name)

    write_json(master_list_path, master_list)

    #update stats
    stats = read_json(f'{dataset_path}/stats.json')
    stats["deleted_posts"] += 1
    write_json(f'{dataset_path}/stats.json', stats)
    return True

#other things
def recount_tagdict(tag_dict: dict) -> dict:
    dataset_dir = f'{dataset_path}'
    tag_dict_path = f'{dataset_dir}/tag_dict.json'

    updated_tags = []
    for folder in os.listdir(dataset_dir):
        if not os.path.isdir(f'{dataset_dir}\{folder}'):
            continue
        log_location = f'{dataset_dir}/{folder}/post_data.json'
        post_data = read_json(log_location)
        del post_data['description'] 

        for post in post_data:
            tags = post_data[post].get('tags')
            if tags == None: 
                pass
                print(f'tags == None @ {post_data[post]}') 
            for tag in tags:
                tag = str(tag).lower()
                if tag not in tag_dict['all']:
                    tag_obj = classes.tag()
                    starter = tag_obj.create_new_tag(tag)
                    tag_dict['all'].update({tag: starter})
                else:
                    if tag not in updated_tags:
                        tag_dict['all'][tag]['count'] = 0
                        updated_tags.append(tag)
                    tag_dict['all'][tag]['count'] += 1
        for tag in tag_dict['all']:
            if (tag not in updated_tags) and (type(tag_dict['all'][tag]) == dict):
                if tag_dict['all'][tag].get('count') != None:
                    #print(f'{tag_dict["all"][tag]} not found in {folder}')
                    tag_dict['all'][tag]['count'] = 0
    if not 'all' in tag_dict.keys():
        create_file(tag_dict_path, classes.tag_dict.starter_dict, 'wj')
    tag_dict['all'] = {dkey : value for dkey, value in sorted(tag_dict['all'].items(), key = lambda ele: ele[0])}
    write_json(tag_dict_path, tag_dict)
    return tag_dict

def update_wiki(modifier_tag: str, update_details: dict):#add automatic replacmet/alias & recount
    dataset_dir = f'{dataset_path}'
    tag_dict_path = f'{dataset_dir}/tag_dict.json'

    modifier_tag = modifier_tag.strip()
    modified_tags = [modifier_tag]
    [[modified_tags.append(tag) for tag in value if (tag != None and tag != 'None')] for value in update_details.values()]

    #update tags
    print(f'@203 || modified tags:{modified_tags}')
    print(f'@204 || UPDATE DETAILS:{update_details}')
    tag_dict = read_json(tag_dict_path)
    for tag in modified_tags:
        if tag in tag_dict['all'].keys():

            if tag in update_details['aliases']:
                tag_dict['all'][tag]['robots']['replace'].append(modifier_tag)

            if tag in update_details['implications']:
                pass

            if tag in update_details['replace']:
                tag_dict['all'][tag]['robots']['aliases'].append(modifier_tag)
                print(f"updating tag at line 217 update post tags {tag_dict['all'][tag]['robots']}")

            if tag in update_details['remove']:
                pass
        else:
            print(f'{tag} not found in dict')
            continue
        tag_dict['all'][tag]['robots'] = {key : list(set(value)) for key, value in tag_dict['all'][tag]['robots'].items()}
        
    if tag_dict != None:
        write_json(tag_dict_path, tag_dict)
    
    update_post_tags()

def update_post_tags():
    global dataset_path
    for folder in os.listdir(dataset_path):
        if not os.path.isdir(f'{dataset_path}\{folder}'):
            continue
        log_location = f'{dataset_path}/{folder}/post_data.json'
        post_data = read_json(log_location) 

        for post in post_data:
            if type(post_data[post]) != dict:
                continue
            tags = post_data[post].get('tags')
            assert type(tags) == list
            tags = tag_cleaner(tags)
            post_data[post]["tags"] = tags
        
        write_json(log_location, post_data)


def update_stats():
    stat_path = f'{dataset_path}/stats.json'
    stats = read_json(stat_path)

    master_list = read_json(f'{dataset_path}/master_list.json')
    total_posts = 0
    cached_post_dict = None
    post_data_dict = None
    for post_id in tqdm.tqdm(master_list["active"]):
        site = post_id.split('_')[0]
        if site != cached_post_dict:
            post_data_dict = read_json(f'{dataset_path}/{site}/post_data.json', False)
            cached_post_dict = site
        if check_post(post_id, post_data_dict) : total_posts += 1
    stats['total_posts'] = total_posts
    stats['deleted_posts'] = len(master_list['deleted'])
    stats['pages'] = total_posts//get_setting('posts_per_page')
    
    tag_dict = read_json(f'{dataset_path}/tag_dict.json')
    tag_dict = recount_tagdict(tag_dict)['all']
    assert type(tag_dict) == dict
    total_tags = 0
    active_tags = 0
    for tag in tag_dict.values():
        if type(tag) != dict:
            continue
        total_tags += 1
        if tag['count'] != 0:
            active_tags += 1
    stats['total_tags'] = total_tags
    stats['active_tags'] = active_tags
    stats['inactive_tags'] = total_tags-active_tags
    stats['valid'] = True

    write_json(stat_path, stats)

def check_post(post_id, post_data_dict) -> bool:
    
    post = classes.post()
    valid = True
    try:
        post.from_id(post_id, post_data_dict)
    except classes.errors.PostNotFound:
        print(f'post not found at {post_id}')
        delete_post(post_id)
        return False
    
    valid = valid and os.path.isfile(post.storage_path)
    valid = valid and (post.mediadata['media_width'] * post.mediadata['media_width'] >= 4)

    if valid:
        return True
    else:
        delete_post(post_id)
        return False

def tag_cleaner(tag_list):
    clean_tags = []
    tag_dict = read_json(f'{dataset_path}/tag_dict.json')['all']
    for tag in tag_list:
        assert type(tag) == str
        tag = tag.strip().replace(' ', '_')
        if tag in tag_dict:
            full_tag = tag_dict[tag]
            full_tag['count'] += 1

            implications = [x for x in full_tag['robots']['implications'] if x != None]
            if len(implications) != 0:
                clean_tags.extend(implications)
                
            replacements = [x for x in full_tag['robots']['replace'] if x != None]
            if len(replacements) != 0:
                clean_tags.extend(replacements)
            else:
                clean_tags.append(tag)
            tag_dict[tag] = full_tag
            #print(full_tag)
        else:
            #print(f'could not find {tag} in full tag dict, creating')
            full_tag = classes.tag()
            full_tag = full_tag.create_new_tag(tag)
            clean_tags.append(tag)
        
    clean_tags = [tag for tag in clean_tags if ((type(tag) == str) and (tag not in ['None', 'none']))]
    #print(clean_tags)
    return(sorted(list(set(clean_tags))))  


def stats_invalid() -> bool:
    'checks if stored stats may be innacurate'
    stat_path = f'{dataset_path}/stats.json'
    stats = read_json(stat_path)
    valid = not bool(stats.get('valid', False))
    ignore = stats.get('ignore', False)
    if ignore == True:
        return False
    return valid

def stats_changed() -> None:
    'changes stats to invalid'
    stat_path = f'{dataset_path}/stats.json'
    stats = read_json(stat_path)
    stats['valid'] = False
    write_json(stat_path, stats)
    #print('stats are now invalid')


def get_setting(setting: str):
    return(read_json(f'{prefix}/config.json')[setting])

def change_setting(setting: str, value):
    file = read_json(f'{prefix}/config.json')
    file[setting] = value
    write_json(f'{prefix}/config.json', file)

import classes
global prefix, dataset_path
cwd = os.path.abspath(os.getcwd())
prefix = f'{cwd}/source'
dataset_path = read_json(f'{prefix}/config.json')["dataset_path"]