#!\venv\Scripts\python.exe
import subprocess, re, requests, PIL.Image, tqdm, time, os
import ffmpeg
import data_manager, classes

global prefix, dataset_path
cwd = os.path.abspath(os.getcwd())
prefix = f'{cwd}/source'
dataset_path = data_manager.read_json(f'{prefix}/config.json')["dataset_path"]

image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'svg', 'gif']
video_extensions = ['mp4', 'webm', 'avi', 'flv', 'mov', 'wmv', 'mkv', 'm4v']

files_downloaded = []

gelbooru_patterns = {
    'posts per page' : 40,
    'page url' : 'https://www.gelbooru.com/index.php?page=post&s=list&tags=all&deleted=show&pid=',
    'total posts' : r'Serving (.*?) posts',  
    'id class' : r'<div class="col thumb" id=".(\d+)">', 
    'post url' : 'gelbooru.com/index.php?page=post&s=view&id=', 
    'post data' : r'<div class="imageContainer"([\S\s]*?)<div id="long-notice">',
    'url' : "https://www.gelbooru.com/",
    'media link' : r'src="https://gelbooru.com//(images.*?)"',
    'original source' : None,
    'uploader id' : r'<a href="index\.php\?page=account&s=profile&id=(.*?)"',
    'uploader name' : r'<a href="index\.php\?page=account&s=profile(.*?)>(.*?)</a>',
    'score' : r'<span id="psc(.*?)">(.*?)</span>',
    'post title' : r'<h6(.*?)</h6>',
    'given tags' : r'<a class="tag-type-(.*?)"(.*?)>(.*?)</a>'
                      }

danbooru_patterns = {
    'posts per page' : 1, # this is set to 1 to hack the fact danbooru uses pages, not ids to determine post's shown
    'page url start' : 'https://danbooru.donmai.us/posts?tags=',
    'page url end' : '&page=',
    'total posts' : r'Serving (.*?) posts',  
    'id class' : r'<article id="post_(.*?)" class="post-preview', 
    'post url' : 'https://danbooru.donmai.us/posts/', 
    'post url suffix' : '.html',
    'post data' : r'<div class="sidebar-container flex sm:flex-col gap-3">([\S\s]+?)<div id="tooltips"></div>',
    'url' : "https://cdn.donmai.us/original/",
    'media link' : r'<a href="https://cdn.donmai.us/original/(.+?)".+?</a>',
    'original source' : r'<li id="post-info-source">Source: <a rel="external noreferrer nofollow" href="(.+?)">.+?</a>',
    'uploader id' : r'Uploader: <a class=".+?" data-user-id="(.+?)"',
    'uploader name' : r'Uploader: <a class=".+?" data-user-id=".+?" data-user-name="(.+?)"',
    'score' : r'<span class="post-score[\S\s]+?>([\d])</a>',
    'post title' : r'<h6(.*?)</h6>',
    'given tags' : r'<a class="search-tag" .+?>(.+?)</a>'
    }

realbooru_patterns = {
    'posts per page' : 40,
    'page url start' : 'https://www.realbooru.com/index.php?page=post&s=list&deleted=show&tags=',
    'page url end' : '&pid=',
    'total posts' : r'Serving (.*?) posts',  
    'id class' : r'<div class="col thumb" id=".(\d+)">', 
    'post url' : 'https://www.realbooru.com/index.php?page=post&s=view&id=', 
    'post url suffix' : '',
    'post data' : r'<div class="col-md-7 col-lg-7 col-xl-8">([\S\s]*?)<div class="col-md-5 col-lg-5 col-xl-4">',
    'url' : "https://www.realbooru.com/",
    'media link' : r'href="https://realbooru\.com//(images.*?)">Original</a>',
    'original source' : None,
    'uploader id' : r'<a href="index\.php\?page=account&s=profile&id=(.*?)"',
    'uploader name' : r'<a href="index\.php\?page=account&s=profile.*?>(.*?)<',
    'score' : r'<span id="psc(.*?)">(.*?)</span>',
    'post title' : r'<h6(.*?)</h6>',
    'given tags' : r'<a class="tag-type-(.*?)"(.*?)>(.*?)</a>'
                      }


def get_mediadata_info(filepath: str) -> dict | None:
    file_extension = filepath.split('.')[-1]
    try:
        if file_extension in image_extensions:
            img = PIL.Image.open(filepath)
            media_width, media_height = img.size
            frame_rate = 0
            length = 0                

        elif file_extension == 'GIF':
            try:
                img = PIL.Image.open(filepath)
                media_width, media_height = img.size
                length = 0
                frames = 0
                while True:
                    try:
                        frames += 1
                        frame_duration = img.info['duration']
                        length += frame_duration
                        img.seek(img.tell() + 1)
                    except EOFError:
                        break
                length = length/1000
                frame_rate = frames/length
            except:
                return None

        else:
            media_info = dict(ffmpeg.probe(filepath))
            media_width = media_info['streams'][0]['width']
            media_height = media_info['streams'][0]['height']
            frame_rate = media_info['streams'][0]['r_frame_rate']
            length = float(media_info["format"]["duration"])          
                
    except Exception as ex:
        print(f'in {filepath} {type(ex)} : {ex}')
        #raise Exception
        media_width = 0
        media_height = 0
        frame_rate = 0
        length = 0       


    mediadata = {
    'media_width': media_width,
    'media_height': media_height,
    'frame_rate': frame_rate,
    'length': length,
    'file_extenstion' : file_extension
    }
    return mediadata

def call_api(url): 
    url = str(url)
    #print(url)
    return requests.get(url, allow_redirects=True).text


def download_post(post_id, website_class, site) -> str:
    global page_dict
    try:
        post = classes.post()

        post_id = int(post_id)
        if post_id in all_downloaded_ids:
            return "continue: already downloaded"
        
        post_url = website_class['post url'] + str(post_id) + website_class['post url suffix']
        id_html = call_api(post_url)
        id_html = re.search(website_class['post data'] , id_html)
        if len(id_html.groups()) > 0: id_html = id_html.groups()[0]
        else: 
            print(id_html.groups())
            raise KeyError

        #parse id_html
        media_link = website_class['url'] + str(re.findall(website_class['media link'], id_html)[-1])
        #print(media_link)
        media_data = requests.get(media_link).content
        file_extension = media_link.split('.')[-1]
        filepath = f'{dataset_path}/{site}/media/{post_id}.{file_extension}'
        with open(filepath, 'wb') as handler:
            files_downloaded.append(post_id)
            handler.write(media_data)

        #get data
        mediadata_info = get_mediadata_info(filepath)
        if mediadata_info == None:
            data_manager.delete_post(f'{site}_{post_id}')
            return "continue"
        
        original_source = website_class['original source']
        uploader_id = re.search(website_class['uploader id'], id_html)
        if uploader_id != None:
            uploader_id = uploader_id.group()

        uploader_name = re.search(website_class['uploader name'], id_html)
        if uploader_name != None:
            uploader_name = uploader_name.group()

        score = re.search(website_class['score'], id_html)
        if score != None:
            score = score.group()

        title = re.search(website_class['post title'], id_html)
        if title != None:
            title = title.group()

        given_tags = [f'general:{x}' for x in re.findall(website_class['given tags'], id_html)]
        rating = 'None'

        mediadata_info.update({'original_source' : original_source, "media_link" : media_link})
        #cleaned_tags = given_tags
        cleaned_tags = tag_cleaner(given_tags)
        post_data = {#mutables first
            'id': f'{site}_{post_id}',
            'tags': cleaned_tags,
            'title': title,
            'mediadata' : mediadata_info,
            'rating': rating,
            'time_catalouged' : round(time.time(),2),
            'uploader_id': uploader_id,
            'uploader_name': uploader_name,
            'score': score,
            'storage_path': filepath
        }
        
        post_data = post.from_json(post_data)

        data_manager.create_post(post)
    except Exception as Ex:
        print(f'error occured at id: {post_id}')
        raise Ex    

def download_page(url, website_class, site): #website_class contains a dict of regex patterns 
    global all_downloaded_ids, files_downloaded
    html = call_api(url)
    try:
        ids_on_page = [int(x) for x in re.findall(website_class['id class'], html)]#returns a list of all ids on page
        page_name = f'{re.findall(r"[.](.*?)[.]", url)[0]}id{ids_on_page[0]}to{ids_on_page[-1]}'
    except IndexError:
        print(f'no posts on {url}')
        return None

    if len(set(all_downloaded_ids+ids_on_page)) <= len(set(all_downloaded_ids)): #checks to see if page is already downloaded by checking if the combined set is bigger than just the previous set <3 I feel so smart
        print(f'already downloaded page')
        return

    for post_id in tqdm.tqdm(ids_on_page, leave=False, position=3):
        result = download_post(post_id, website_class, site)

    return(ids_on_page)
    

def tag_cleaner(tag_list):
    clean_tags = []
    for tag in tag_list:
        tag = tag.split(':')[-1]
        correction_found = False
        data_manager.read_json(f'{dataset_path}/tag_dict.json')
        '''
        for mapping in tag_dict:
            if re.fullmatch(mapping[1], tag) != None:
                correction_found = True
                if mapping[0] == 'alias':
                    clean_tags.append(mapping[2])

                if mapping[0] == 'implication':
                    clean_tags.append(mapping[2])
                    clean_tags.append(tag)

                if mapping[0] == 'substitution':
                    clean_tags.append(re.sub(mapping[1], tag))
        '''
        if correction_found == False:
            clean_tags.append(tag)
        
    clean_tags = [re.sub(r' ', '_', x) for x in clean_tags]
    #print(clean_tags)
    return(sorted(list(set(clean_tags))))  

def iterate():
    global all_downloaded_ids, files_downloaded, prefix
    data_manager.create_all()
    start = time.time()
    total_ids = int(input("total ids: "))
    site = str(input("site: "))
    tags = str(input("tags: "))
    if tags == '' and site == 'realbooru': tags = "all"
    else: tags = re.sub(r' ', '+', tags)
    site_patterns = globals()[f'{site}_patterns']

    data_manager.create_site(site)

    ids_to_download = total_ids-1
    page_index = 1 #start from id 0
    pids = []
    while ids_to_download > 0:
        pids.append(page_index)
        page_index += site_patterns['posts per page']
        ids_to_download -= site_patterns['posts per page']

    master_list_path = f'{dataset_path}/master_list.json'
    master_list = data_manager.read_json(master_list_path)
    all_downloaded_ids = master_list[site]
    for i in tqdm.tqdm(pids, position=1):

        url = f'{site_patterns["page url start"]}{tags}{site_patterns["page url end"]}{i}'
        #print(url)
        if download_page(url, site_patterns, site) == None:
            break

    
    print(f'done in {round(time.time()-start, 2)} seconds')
    print(f'{len(files_downloaded)} new files downloaded')
    try:
        all_downloaded_ids
    except: 
        all_downloaded_ids = files_downloaded
    print(f'{len(all_downloaded_ids)} total files downloaded')
    files_downloaded = []
    all_downloaded_ids = None

if __name__ == '__main__':
    data_manager.create_all()
    iterate()

