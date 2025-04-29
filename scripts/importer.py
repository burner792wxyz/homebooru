#!\venv\Scripts\python.exe
import subprocess, re, requests, PIL.Image, tqdm, time, os
import ffmpeg
import data_manager, classes

global prefix, dataset_path
cwd = os.path.abspath(os.getcwd())
prefix = f'{cwd}/source'
dataset_path = data_manager.read_json(f'{prefix}/config.json')["dataset_path"]

image_extensions = ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff', 'svg']
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
    'posts per page' : 20,
    'page increment' : 1,
    'page url start' : 'https://danbooru.donmai.us/posts?tags=',
    'page url end' : '&page=',
    'total posts' : r'Serving (.*?) posts',  
    'id class' : r'<article id="post_(.*?)" class="post-preview', 
    'post url' : 'https://danbooru.donmai.us/posts/', 
    'post url suffix' : '.html',
    'post data' : r'<div class="sidebar-container flex sm:flex-col gap-3">([\S\s]+?)<div id="tooltips"></div>',
    'url' : "https://cdn.donmai.us/original/",
    'media link' : r'<a href="https://cdn.donmai.us/original/(.+?)".+?</a>',
    'original source' : r'<li id="post-info-source">Source: .*? href="(.*?)">',
    'uploader id' : r'Uploader: <a class=".+?" data-user-id="(.+?)"',
    'uploader name' : r'Uploader: <a class=".+?" data-user-id=".+?" data-user-name="(.+?)"',
    'score' : r'<span class="post-score[\S\s]+?>([\d])</a>',
    'post title' : r'<h6(.*?)</h6>',
    'given tags' : r'<a class="search-tag" .+?>(.+?)</a>'
    }

realbooru_patterns = {
    'posts per page' : 40,
    'page increment' : 40,
    'page url start' : 'https://www.realbooru.com/index.php?page=post&s=list&deleted=show&tags=',
    'page url end' : '&pid=',
    'total posts' : r'Serving (.*?) posts',  
    'id class' : r'<div class="col thumb" id=".(\d+)">', 
    'post url' : 'https://www.realbooru.com/index.php?page=post&s=view&id=', 
    'post url suffix' : '',
    'post data' : r'<div class="col-md-7 col-lg-7 col-xl-8">([\S\s]*?)<div class="col-md-5 col-lg-5 col-xl-4">',
    'url' : "https://www.realbooru.com/",
    'media link' : r'(images.*?)">Original',#<a.+?>Original</a>
    'original source' : r'Source.+?<.+?value="(.+?)"',
    'uploader id' : r'<a href="index\.php\?page=account&s=profile&id=(.*?)"',
    'uploader name' : r'<a href="index\.php\?page=account&s=profile.*?>(.*?)<',
    'score' : r'<span id="psc.*?">(.*?)</span>',
    'post title' : r'<h6>(.*?)</h6>',
    'given tags' : r'<a class="tag-type-.*?>(.*?)</a>'
}


def get_mediadata_info(filepath: str) -> dict | None:
    file_extension = filepath.split('.')[-1]
    try:
        if file_extension in image_extensions:
            img = PIL.Image.open(filepath)
            media_width, media_height = img.size
            frame_rate = 0
            length = 0                

        elif file_extension.upper() == 'GIF':
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
            except Exception as ex:
                print(ex)
                return None

        else:
            media_info = dict(ffmpeg.probe(filepath))
            media_width = media_info['streams'][0]['width']
            media_height = media_info['streams'][0]['height']
            frame_rate = media_info['streams'][0]['r_frame_rate']
            length = float(media_info["format"]["duration"])          
                
    except Exception as ex:
        print(f'in {filepath} {type(ex)} : {ex}')
        return None    


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


def download_post(post_id, website_class, site) -> bool:
    global page_dict
    try:
        post = classes.post()

        post_name = f'{site}_{post_id}'
        if post_name in all_downloaded_ids:
            return False
        
        post_url = website_class['post url'] + str(post_id) + website_class['post url suffix']
        id_html = call_api(post_url)
        id_html = re.search(website_class['post data'] , id_html)
        #data_manager.create_file(f'{dataset_path}/{post_id}.html', str(id_html.groups()))
        if len(id_html.groups()) > 0: id_html = id_html.groups()[0]
        else: 
            print(id_html.groups())
            raise KeyError

        #parse id_html
        rel_link = re.search(website_class['media link'], id_html)
        if rel_link == None:
            data_manager.create_file(f'{prefix}/a.html', id_html)
            print('could not find media link')
            return False
        rel_link = rel_link.group(1)
        media_link = website_class['url'] + rel_link
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
            return False
        
        original_source = re.search(website_class['original source'], id_html)
        if original_source != None:
            original_source = original_source.group(1)

        uploader_id = re.search(website_class['uploader id'], id_html)
        if uploader_id != None:
            uploader_id = uploader_id.group(1)

        uploader_name = re.search(website_class['uploader name'], id_html)
        if uploader_name != None:
            uploader_name = uploader_name.group(1)

        score = re.search(website_class['score'], id_html)
        if score != None:
            score = score.group(1)
        else:
            score = 0

        title = re.search(website_class['post title'], id_html)
        if title != None:
            title = title.group(1)

        given_tags = [f'{x.group(1)}' for x in re.finditer(website_class['given tags'], id_html)]
        rating = 'None'

        mediadata_info.update({'original_source' : original_source, "media_link" : media_link})
        #cleaned_tags = given_tags
        cleaned_tags = data_manager.tag_cleaner(given_tags)
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
        return True
    except Exception as Ex:
        print(f'error occured at id: {post_id}')
        raise Ex

def download_page(url, website_class, site): #website_class contains a dict of regex patterns 
    global all_downloaded_ids, downloaded_ids, total_ids, pbar
    
    html = call_api(url)
    try:
        ids_on_page = [int(x) for x in re.findall(website_class['id class'], html)]#returns a list of all ids on page
        page_name = f'{re.findall(r"[.](.*?)[.]", url)[0]}id{ids_on_page[0]}to{ids_on_page[-1]}'
    except IndexError:
        print(f'no posts on {url}')
        raise classes.errors.EmptyPage

    for post_id in ids_on_page:
        result = download_post(post_id, website_class, site)
        #print(post_id, result, downloaded_ids)
        if result == True:
            downloaded_ids += 1
            pbar.update(1)
        if downloaded_ids >= total_ids:
            return

def iterate():
    global all_downloaded_ids, prefix, total_ids, downloaded_ids, pbar
    data_manager.create_all()
    start = time.time()
    total_ids = int(input("total ids: "))
    site = str(input("site: "))
    tags = str(input("tags: "))
    if tags == '' and site == 'realbooru': tags = "all"
    else: tags = re.sub(r' ', '+', tags)
    site_patterns = globals()[f'{site}_patterns']

    data_manager.create_site(site)
    master_list_path = f'{dataset_path}/master_list.json'
    master_list = data_manager.read_json(master_list_path)
    all_downloaded_ids = master_list["active"] + master_list["deleted"]

    downloaded_ids = 0
    i=1
    pbar = tqdm.tqdm(total=total_ids)
    while downloaded_ids < total_ids:
        url = f'{site_patterns["page url start"]}{tags}{site_patterns["page url end"]}{i}'
        try:
            download_page(url, site_patterns, site)
        except classes.errors.EmptyPage:
            break
        i += site_patterns['page increment']
    pbar.close()

    print(f'\ndone in {round(time.time()-start, 2)} seconds')
    print(f'{downloaded_ids} new files downloaded')
    print(f'{len(all_downloaded_ids)+downloaded_ids} total files downloaded')

if __name__ == '__main__':
    iterate()

