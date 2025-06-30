'''
module that defines all data classes used in homebooru
'''
import random, os, time
import data_manager

global prefix, dataset_path
cwd = os.path.abspath(os.getcwd())
prefix = f'{cwd}/source'
dataset_path = data_manager.read_json(f'{prefix}/config.json')["dataset_path"]

class errors:
    class PostNotFound(Exception):
        pass  
    class EmptyPage(Exception):
        pass


class tag_dict:
    starter_dict = {"description":"dictionary of tags", "all" : {}}

class search_methods:
    post_sort_methods = {
        "id" : "sort posts by id, highest first",
        "tag_count" : "sort posts by number of tags, highest first",
        "time_catoluged" : "sort by time catoluged, most recent first",
        "uploader_id" : "sort by uploader id, highest first",
        "score" : "sort by score on original site, highest first",
        "rank" : "sort by rank assigned on homebooru, highest first",
        "random" : "sorts post by random",
        "width" : "sorts by width of media, widest first",
        "height" : "sorts by height of media, tallest first",
        "length" : "sorts by duration of media, longest first",
        "file_size" : "sort by size of media, largest first"
    }
    post_sort_aliases = {}

class master_list:
    starter_dict = {
        "description":"list of posts",
        "master":[],
        "active":[],
        'deleted':[]
        }

class settings:
    pass

class stats:
    start_dict = {
        "total_posts" : 0,
        "deleted_posts": 0,
        "total_tags" : 0,
        "active_tags" : 0,
        "inactive_tags" : 0,
        "valid" : False,
        'ignore' : False

    }

class user:

    class_type = "user class"

    def __init__(self, user_id, user_name=None, favorite_posts=None, favorite_searches=None, blacklist=None):
        self.user_id = user_id
        self.user_name = user_name
        self.favorite_posts = favorite_posts
        self.favorite_searches = favorite_searches
        self.blacklist = blacklist
        self.user_dict = None

    def create_dict(self):
        self.data_dictionary = {
            str(self.user_id) : {
                "user_id" : self.user_id,
                "user_name" : self.user_name,
                "favorite_posts" : self.favorite_posts,
                "favorite_searches" : self.favorite_searches,
                "blacklist" : self.blacklist
            }        
        }
    
class post:
    """
    class for posts containing a video or image
    """
    class_type = "post class"

    def __init__(self):
        self.id = None        
        self.invalid = str(''.join([chr(random.randint(33, 125)) for x in range(0, 100)]))

    def from_json(self, post_data: dict, strict = False):
        """
        formats the post data from a json dictionary
        """
        checksum = hash(str(post_data))

        if self.id == None:
            self.id = post_data.get("id", self.invalid)
        self.site, self.num_id = self.id.split('_')
        
        self.tags = post_data.get("tags", self.invalid)
        self.title = post_data.get("title", self.invalid)
        self.mediadata = post_data.get("mediadata", self.invalid)
        self.rating = post_data.get("rating", self.invalid)
        self.time_catalouged = round(float(post_data.get("time_catalouged", 0)))
        self.uploader_id = post_data.get("uploader_id", self.invalid)
        self.uploader_name = post_data.get("uploader_name", self.invalid)
        self.score = post_data.get("score", self.invalid)
        self.storage_path = str(post_data.get("storage_path", self.invalid))
        self.data_path = str(post_data.get("data_path", self.invalid))
        self.rank = post_data.get("rank", self.invalid)

        self.mediadata = {
            "media_width" : self.mediadata.get("media_width", self.invalid),
            "media_height" : self.mediadata.get("media_height", self.invalid),
            "frame_rate" : self.mediadata.get("frame_rate", self.invalid),
            "length" : self.mediadata.get("length", self.invalid),
            "file_extenstion" : self.mediadata.get("file_extenstion", self.invalid),
            "original_source" : self.mediadata.get("original_source", self.invalid),
            "media_link" : self.mediadata.get("media_link", self.invalid),
            "file_size" : self.mediadata.get("file_size", self.invalid)
        }
        if os.access(self.storage_path, os.R_OK): #if file is readable
            self.mediadata["file_size"] = os.stat(self.storage_path).st_size
            self.data_path = f'{os.path.dirname(os.path.dirname(self.storage_path))}/post_data.json'
            #print(f'self.data_path: {self.data_path}')
        else:
            raise FileNotFoundError(f'file at {self.storage_path} is not readable, check permissions or file path')
            self.storage_path = "invalid path"
            self.data_path = "invalid path"
        if ((strict) and (self.invalid in self.mediadata.values())):
            raise KeyError(self.mediadata)
        self.mediadata = {key: ((None if (self.invalid in value) else value) if isinstance(value, str) else value) for key, value in self.mediadata.items()}


        self.data_dictionary = {
            "id" : self.id,
            "tags" : self.tags,
            "title" : self.title,
            "mediadata" : self.mediadata,
            "rating" : self.rating,
            "time_catalouged" : self.time_catalouged,
            "uploader_id" : self.uploader_id,
            "uploader_name" : self.uploader_name,
            "score" : self.score,
            "storage_path" : self.storage_path,
            "data_path" : self.data_path,
            "rank" : self.rank
        }
        if ((strict) and (self.invalid in self.data_dictionary.values())):
            raise KeyError(self.data_dictionary)
        self.data_dictionary = {key: ((None if (self.invalid in value) else value) if isinstance(value, str) else value) for key, value in self.data_dictionary.items()}

        #update file if neccesary and possible
        if ((hash(str(self.data_dictionary)) != checksum) and (self.data_path != "invalid path")):
            #print(f'updated post file at: {self.data_path}')
            data_manager.create_post(self)
        return self.data_dictionary

    def from_id(self, pid="self.id", post_json=None):
        """
        gets post data from existing post in dataset
        """
        if pid != "self.id":
            self.id = pid
        assert type(self.id) == str
        
        self.site, self.num_id = self.id.split('_')
        post_path = f'{dataset_path}/{self.site}/post_data.json'
        if post_json == None:
            post_json = data_manager.read_json(post_path, False)
            if post_json == None:
                raise Exception(f'{post_path} has empty post data')
        if not str(self.num_id) in post_json.keys():
            raise errors.PostNotFound()
        post_json = post_json[str(self.num_id)]

        self.from_json(post_json)
        
        return None

class tag:
    class_type = "tag class"
    cwd = os.path.abspath(os.getcwd())
    data_path = f'{dataset_path}/tag_dict.json'
    def __init__(self):        
        self.invalid = str(''.join([chr(random.randint(33, 125)) for x in range(0, 100)]))

    def create_new_tag(self, tag_name):
        num_id = data_manager.get_setting("tag_count")
        data_manager.change_setting("tag_count", num_id+1)
        self.robots = {
            "aliases" : [None],
            "implications" : [None],
            "replace" : [None],
            "remove" : [None]
        }

        self.data_dictionary = {
            "name" : tag_name,
            "id" : num_id,
            "count" : 1,
            "description" : None,
            "last_edit" : round(time.time(),2),
            "category" : None,
            "robots" : self.robots
        }
        all_tags = data_manager.read_json(tag.data_path)
        all_tags['all'][str(tag_name)] = self.data_dictionary
        data_manager.write_json(tag.data_path, all_tags)
        return self.data_dictionary

    def format_dict(self, tag_data: dict, strict = False):
        checksum = hash(str(tag_data))
        #print(f'@207 in tag class || tag data: {tag_data}')

        self.name = tag_data.get("name", self.invalid)
        self.count = tag_data.get("count", self.invalid)
        self.description = tag_data.get("description", self.invalid)
        self.last_edit = tag_data.get("last_edit", self.invalid)
        self.category = tag_data.get("category", self.invalid)
        self.robots = tag_data.get("robots", {})

        self.robots = {
            "aliases" : self.robots.get("aliases", self.invalid),
            "implications" : self.robots.get("implications", self.invalid),
            "replace" : self.robots.get("replace", self.invalid),
            "remove" : self.robots.get("remove", self.invalid)
        }

        if ((strict) and (self.invalid in self.robots.values())):
            raise KeyError(self.mediadata)
        self.robots = {key: (([None] if (self.invalid in value) else value) if isinstance(value, str) else value) for key, value in self.robots.items()}


        self.data_dictionary = {
            "name" : self.name,
            "count" : self.count,
            "description" : self.description,
            "last_edit" : self.last_edit,
            "category" : self.category,
            "robots" : self.robots
        }
        if ((strict) and (self.invalid in self.data_dictionary.values())):
            raise KeyError(self.data_dictionary)
        self.data_dictionary = {key: (([None] if (self.invalid in value) else value) if isinstance(value, str) else value) 
                                for key, value in self.data_dictionary.items()}

        #update file if neccesary and possible
        if ((hash(str(self.data_dictionary)) != checksum) and (tag.data_path != "invalid path")):
            print(f'updated post file at: {tag.data_path}')
            full_dictionary = data_manager.read_json(tag.data_path)
            full_dictionary[str(self.name)] = self.data_dictionary
            data_manager.write_json(self.data_path, full_dictionary)
        return self.data_dictionary
    
def format_size(size: int) -> str:
    units = ['B', 'kB', 'MB', 'GB']
    i = 0
    while size >= 1000:
        size = size/1000
        i += 1
    unit = units[i]
    return(f'{round(size,2)}{unit}')