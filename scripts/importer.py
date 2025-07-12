#!\venv\Scripts\python.exe
import re, requests, PIL.Image, tqdm, time, os, validators#type: ignore
import yt_dlp as yt #type: ignore
import ffmpeg
import data_manager, classes

global prefix, dataset_path
cwd = os.path.abspath(os.getcwd())
prefix = f'{cwd}/source'
dataset_path = data_manager.read_json(f'{prefix}/config.json')["dataset_path"]

blacklist = ['logo', 'icon', '.js']

image_extensions = ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff', 'svg', 'gif']
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
    'score' : r'<a rel="nofollow" href="/post_votes\?.+?>(.*?)</a>',
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


def get_mediadata_info(filepath: str, original_source=None) -> dict | None:
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
    'file_extenstion' : file_extension,
    'original_source': original_source
    }
    return mediadata

def call_api(url): 
    url = str(url)
    if not validators.url(url):
        print(f'Invalid URL: {url}')
        return None
    #print(url)
    return requests.get(url, allow_redirects=True).text

def get_media_htmls(html: str) -> list:
    html = re.sub(r'[\n]', ' ', html)#remove new lines
    pattern = re.compile(r'(<img.*?>)|(<video[\s\S]*?</video>)')
    media_htmls = [str(''.join(x)) for x in re.findall(pattern,html)]
    return media_htmls
 
def get_data(website_class, id_html, key):
        data = re.search(website_class[key], id_html)
        if data != None:
            data = data.group(1)
        return(data)

def get_media_from_url(post_url, path, always_use_yt_dlp=True):
        '''
        Downloads media from a post URL and returns the HTML of the post, number of media files downloaded, and a list of tuples containing the media source and file path.
        '''
        print(f'\n downloading media from {post_url}')
        if post_url.split('.')[-1] in video_extensions or post_url.split('.')[-1] in image_extensions:
            #if the post url is a direct link to a media file, download it directly
            media_data = requests.get(post_url).content
            file_extension = post_url.split('.')[-1].split('?')[0]
            if file_extension not in image_extensions + video_extensions:
                print(f'unknown file extension: {file_extension} for {post_url}')
                return None, 0, []
            filepath = f'{path}.{file_extension}'
            with open(filepath, 'wb') as handler:
                handler.write(media_data)
                media_info = get_mediadata_info(filepath, original_source=media_src)
            return None, 1, [{"source" : post_url, "filepath" : filepath, "media_data" : media_info}]
        id_html = call_api(post_url)
        if id_html == None:
            print(f'no html found for {post_url}')
            return None, 0, []
        media_htmls = get_media_htmls(id_html)
        media_downloaded = 0
        media_objs = []
        if len(media_htmls) == 0:
            print(f'no media found for {post_url}')
        else:
            for i, media in enumerate(media_htmls):
                if any([x in media for x in blacklist]):
                    print(f'skipping media with blacklisted content: {media}')
                    continue
                media_src = re.search(r'src="(.*?)"', media)
                if media_src == None:
                    continue
                media_src = media_src.groups()[0]
                if media_src.startswith("https://"):
                    pass
                elif media_src.startswith("http://"):
                    pass
                else:
                    media_src = "http:" + media_src
                if not validators.url(media_src):
                    continue
                raw_media_data = requests.get(media_src).content
                file_extension = media_src.split('?')[0].split('.')[-1]
                if file_extension not in image_extensions + video_extensions:
                    print(f'unknown file extension: {file_extension} for {media_src}')
                    continue
                filepath = f'{path}_{i}.{file_extension}'
                with open(filepath, 'wb') as handler:
                    handler.write(raw_media_data)
                    media_info = get_mediadata_info(filepath, original_source=media_src)
                    media_downloaded += 1
                    media_objs.append({"source" : media_src, "filepath" : filepath, "media_data" : media_info})
        if media_downloaded == 0 or always_use_yt_dlp:
            #try using yt-dlp to download media
            print(f'trying yt-dlp')
            try:
                ydl_opts = {
                    'outtmpl': f'{path}_%(id)s.%(ext)s',
                    'format': 'bestvideo+bestaudio/best',
                    'noplaylist': True,
                    'quiet': True,
                    'socket_timeout': 30,
                }
                with yt.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(post_url, download=True)
                    media_src = info_dict.get('url', None)
                    file_extension = info_dict.get('ext', None)
                    if media_src and file_extension:
                        filepath = f'{path}_{media_downloaded+1}.{file_extension}'
                        yt_dlp_filename = f'{path}_{info_dict["id"]}.{file_extension}'
                        os.rename(yt_dlp_filename, filepath)
                        media_downloaded += 1
                        media_objs.append({"source" : media_src, "filepath" : filepath, "media_data" : info_dict})
            except Exception as e:
                print(f'Error downloading media with yt-dlp: {e}')
                #print(f'html: {id_html}')
        if media_downloaded == 0:
            print(f'no media downloaded for {post_url}')
            print(f'html: {id_html}')
            return id_html, 0, []
        return id_html, media_downloaded, media_objs
def get_tags_from_url(url) -> list:#still experimental
    html = call_api(url)
    if html == None:
        print(f'no html found for {url}')
        return []
    tags = re.findall(r'<(.*?tags.*?)>', html)
    tags = [tag for tag in tags if tag.startswith('section')]#gets tags element
    if len(tags) == 0:
        print(f'no tags found in {url}')
        return []
    tags = re.findall(r'"(.*?)"', tags[0])#gets all tags in the element
    tags = sorted(tags, key=lambda x: len(re.sub(r'[^ ]', '', x)) if (x != None) else 0, reverse=True)[0] #find the tag with the most spaces
    return tags

def download_post(post_id, website_class, site) -> bool:
    global page_dict, blacklist
    try:
        post = classes.post()
        post_name = f'{site}_{post_id}'
        if post_name in all_downloaded_ids:
            return False
        
        post_url = website_class['post url'] + str(post_id) + website_class['post url suffix']
        filepath = f'{dataset_path}/{site}/media/{post_id}'
        id_html, media_downloaded, media_objs = get_media_from_url(post_url, filepath)
        if media_downloaded == 0: return
        filepath = media_objs[0][1] #use first media file as the post file

        id_html = re.search(website_class['post data'] , id_html)
        if len(id_html.groups()) > 0: id_html = id_html.groups()[0]
        else: 
            print(id_html.groups())
            raise KeyError

        #get data
        mediadata_info = get_mediadata_info(filepath)
        if mediadata_info == None:
            data_manager.delete_post(f'{site}_{post_id}')
            return False
        
        original_source = get_data(website_class, id_html, 'original source')
        uploader_id = get_data(website_class, id_html, 'uploader id')
        uploader_name = get_data(website_class, id_html, 'uploader name')
        title = get_data(website_class, id_html, 'post title')
        score = get_data(website_class, id_html, 'score')
        if score == None:
            score = 0

        given_tags = [f'{x.group(1)}' for x in re.finditer(website_class['given tags'], id_html)]
        rating = 'None'

        mediadata_info.update({'original_source' : original_source, "media_link" : media_objs[0][0]})
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