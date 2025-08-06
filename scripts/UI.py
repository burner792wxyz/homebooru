#!\venv\Scripts\python.exe
r'''
run in venv powershell by executing:
    .venv\Scripts\Activate.ps1
    python source/scripts/UI.py
'''
import thumbnailizer, post_checker, importer, data_manager, classes #own scripts
import flask, os, re, math, socket, time, tqdm, random, logging

posts_per_page = data_manager.get_setting('posts_per_page')

global prefix, dataset_path
cwd = os.path.abspath(os.getcwd())
prefix = f'{cwd}/source'
dataset_path = data_manager.read_json(f'{prefix}/config.json')["dataset_path"]

media_keys = ['media_link', 'media_width', 'media_height', 'frame_rate', 'length', 'original_source']
immutables = ["storage_path", "score", "id", "mediadata", "uploader_id"]
#helper functions

def pagechange() -> list:
    data_manager.clean_temp()
    messages = flask.get_flashed_messages(with_categories=True)
    return messages if messages else []

def build_post_html(passed_ids, all_post_data) -> tuple[list[str], list[str]]:
    icon_prefix = f'{prefix}\\static\\icons'
    rank_paths = {
        'None' : 'undefined.png',
        '0' : '0.png',
        '1' : '1.png',
        '2' : '2.png',
        '3' : '3.png',
        '4' : '4.png'
    }

    tag_dict = {}
    post_html_list = []

    for post_name in passed_ids:#build html of posts
        post_site, post_id = post_name.split('_')
        post_data = all_post_data[post_site][post_id]

        for tag in post_data['tags']:
            if tag in tag_dict.keys():
                tag_dict[tag] += 1
            else:
                tag_dict.update({tag : 1})
        filename = re.sub('\\'+'\\', '/', post_data["storage_path"])
        img_path = flask.url_for('preview', filename=filename, mode='preview')
        rank_path = flask.url_for('preview', filename=f'{icon_prefix}\\{rank_paths[str(post_data["rank"])]}', mode='preview')
        if post_data['mediadata']['length'] > 0: 
            media_class = 'video'
        else: 
            media_class = 'image'

        post_html = {
            "name": post_name,
            "id" : post_id, 
            "site": post_site, 
            'tags': post_data["tags"], 
            'img_src' : img_path,
            'rank_src' : rank_path,
            'media_class': media_class
            }
        post_html_list.append(post_html)
    
    tag_list = sorted(tag_dict, key= lambda i: tag_dict[i], reverse=True)[0:20]
    return(tag_list, post_html_list)

def paginator(search, id_list, page = None) -> list:
    global posts_per_page
    id_list = set(id_list)
    if page == None:
        page = int(search.get('page', 0))
    extra_args = '&'+'&'.join([f'{key}={"+".join(value)}' for key, value in search.items()])
    if extra_args == '&': extra_args = ''
    pageinator = []

    total_posts = len(id_list)
    last_page = math.ceil(total_posts/posts_per_page)-1

    radius_of_paginator = 3
    curr_page = int(page-(radius_of_paginator//1))
    added_pages = 0
    if page > 0:
        pageinator.append(f'<a href="/posts?page={min(last_page, page-1)}{extra_args}" class="page-link">&lt;</a> \n')

    while True:#makes sure there is the maximum amount of pages in the paginator, even if there are more pages on one side of starting page
        #print(f'real_page: {page}, current page: {curr_page}, last page : {last_page}')
        if curr_page < 0:
            curr_page += 1
            continue
        if curr_page == page:
            pageinator.append(f'<span class="page-link">{page}</span> \n')
        elif (curr_page <= last_page) and (added_pages <= radius_of_paginator*2):
            pageinator.append(f'<a href="/posts?page={curr_page}{extra_args}" class="page-link">{curr_page}</a> \n')
        curr_page += 1
        added_pages += 1

        if curr_page > last_page:
            #print(f'breaking from paginator while loop')
            break
    if page < last_page:
        pageinator.append(f'<a href="/posts?page={page+1}{extra_args}" class="page-link"> &gt; </a> \n') 
    return pageinator

def is_iterable(obj):
    if type(obj) == str:
        return False
    try:
        iter(obj)
        return True
    except:
        return False

def terminate_server():
    os._exit(0)

def print_times(times: dict, merged = False) -> None:
    if merged:
        split_times = {}
        for key, value in times.items():
            if '/' in key:
                split = key.split('/')
                for split_key in split:
                    split_times.update({split_key : value})
            else : 
                split_times.update({key : value})
        times = split_times

    starts = {str(x).replace('*start*', '').strip() : y for x, y in times.items() if '*start*' in x}#str(x).replace('*start*', '')
    ends = {str(x).replace('*end*', '').strip() : y for x, y in times.items() if '*end*' in x}#str(x).replace('*end*', '')
    durations = {}
    for start in starts.keys():
        item_time = round((ends[start] - starts[start])*1000,3)
        durations.update({start : item_time})
        print(f'{start}: took {item_time} miliseconds')
    print(f'total : {round(sum(durations.values()),3)} miliseconds')

def needs_new_cache(current_page, cache_start_page):
    global page_buffer
    cache_end_page = cache_start_page + page_buffer - 1
    return current_page < cache_start_page or current_page > cache_end_page

def format_link(link: str) -> str:
    link = str(link)
    if '.' in link:
        name = link.split('.')[1]
        href = re.sub(r'www\.', '', link)
        link = f'<a href ="{href}">{name}</a>'
        return link
    return ' None '

def format_post_data(post_data):
    post = classes.post()
    post_data = post.from_json(post_data)
    tag_htmls = []
    for tag in sorted(post_data['tags']):
        wiki_link = f'/wiki/{tag}'
        search_link = f'/posts?tags={tag}'
        tag_html =f'''
<a class="wiki-link" href={wiki_link}>?</a>
<a class="search-link" href="{search_link}">{tag.replace('_', ' ')}</a>
'''
        tag_htmls.append(tag_html)

    true_size = classes.format_size(int(post_data["mediadata"]["file_size"]))
    other_postdata = {
    "ID" : str(post_data["id"]),
    "Uploader" : str(post_data["uploader_name"]),
    "Date" : str(time.strftime('%Y-%m-%d %H:%M', time.gmtime(post_data["time_catalouged"]))),
    "Size" : f'{true_size} {post_data["mediadata"]["media_width"]}x{post_data["mediadata"]["media_height"]}x{post_data["mediadata"]["length"]}',
    "Source" : f'{format_link(post_data["mediadata"]["original_source"])} & {format_link(post_data["mediadata"]["media_link"])}',
    "Rating" : str(post_data["rating"] ),
    "Score" : str(post_data["score"] ),
    "Homebooru_Rank" : str(post_data["rank"]),
    "Filepath" : str(post_data["storage_path"])
    }
    
    return(tag_htmls, other_postdata)

def get_id_list(all_post_data: dict, sort_value = "time_catalouged", safe=True):
    broken_ids = []
    #sorting function takes a tag
    if safe:
        def sorting_function(post_name):
            if sort_value == "random":
                return random.random()
            post_site, post_id = post_name.split('_')
            try:
                num = all_post_data[post_site][post_id][sort_value]
                if (num == None) or (num == "None"):
                    raise KeyError
                num = float(num)
            except:
                broken_ids.append(post_name)
                return 0

            return num
    elif sort_value == "random":
        sorting_function = lambda i: random.random()
    else:
        sorting_function = lambda i: all_post_data[i.split('_')[0]].get(i.split('_')[1], {}).get(sort_value, 0)

    if ("asc" in sort_value):
        sort_value = '_'.join(sort_value.split('_')[:-1])
        reverse = False
    else:
        reverse = True
    print(reverse)

    print(f'borken ids {broken_ids}')

    id_list = data_manager.read_json(f'{dataset_path}\master_list.json')
    id_list = sorted(set(id_list["active"]), key=sorting_function, reverse=reverse)
    id_list = [x for x in id_list if x not in broken_ids]
    return(id_list)  

def parse_args(url = None) -> dict:
    'parses args correctly'
    #get arg str
    if url == None:
        start_arg_str = flask.request.query_string.decode()
    else:
        assert type(url) == str
        start_arg_str = ''.join(url.split('?')[1:])
    encoded_chars = re.findall(r'%([\d][\d])', start_arg_str)
    encoded_chars = [chr(int(x, 16)) for x in encoded_chars]
    i = -1
    end_arg_str = ''
    for j, char in enumerate(start_arg_str):
        if j == 0 :
            prev_two = ''
        elif j == 1:
            prev_two = start_arg_str[0]
        else:
            prev_two = start_arg_str[j-2:j]

        if char == '%':
            end_arg_str += encoded_chars[i]
            i+=1
        elif '%' in prev_two:
            continue
        else:
            end_arg_str += char
    #get arg dict
    if 'parent_href=' in end_arg_str:
        parent_href = end_arg_str[end_arg_str.index("'''"):]
        depth = 0
        for i, char in enumerate(parent_href):
            if i > 1:
                sub_str = parent_href[i-2:i+1]
            else:
                continue

            if sub_str == "'*'":
                depth -= 1
            elif sub_str == "'''":
                depth += 1

            if depth == 0:
                parent_href = parent_href[3:i-2]
                break
    if 'parent_href=' in end_arg_str:
        end_arg_str = end_arg_str.replace(f"parent_href='''{parent_href}'*'", '')
    else:
        parent_href = None
    args = {'parent_href' : parent_href}
    other_args = end_arg_str.split('&')
    for arg in other_args:
        if '=' in arg:
            print(arg)
            key, value = arg.split('=') 
            args.update({str(key) : value})
    return(args)

def search_func(page, tags):
    global dataset_path
    sort = "time_catalouged"
    if tags != None:
        tags = tags.copy()    
        for i, tag in enumerate(tags):
            if "sort" in tag.lower() or "order" in tag.lower():
                sort = tag.split(':')[-1]
                del tags[i]
        tags = {'tags' : tags}
    else:
        tags = {}

    all_sites = [f'{path}/post_data.json' for path in [f'{dataset_path}/{x}' for x in os.listdir(dataset_path)] if os.path.isdir(path)]
    all_post_data = {site.split('/')[-2] : data_manager.read_json(site) for site in all_sites}

    #sort master_list of ids
    id_list = get_id_list(all_post_data, sort_value=sort)
    #search
    passed_ids = []
    for post in tqdm.tqdm(id_list):
        if len(passed_ids) >= (page+5)*posts_per_page+2: 
            print(f'finished checking posts at: {(page+1)*posts_per_page+2}')
            break
        if (tags == []) or (tags == {'tags': []}):
            passed_ids.append(post)
        else:
            post_site, post_id = post.split('_')
            post_data = all_post_data[post_site][post_id]
            post_status = post_checker.post_checker(post_data, tags)
            if not post_status:
                continue
            else:
                #print(f'\n {post}')
                passed_ids.append(post)
    return all_post_data, passed_ids

#flask loop
app = flask.Flask(__name__, static_folder = f'{prefix}/static', template_folder = f'{os.path.abspath(os.getcwd())}/source/templates')
#helper views
@app.route('/preview/<path:filename>')
def preview(filename):
    mode = flask.request.args.get('mode', 'original')
    rank = flask.request.args.get('rank', None)
    if mode == 'preview':
        filename = str(thumbnailizer.convert(filename))

    if not os.path.exists(filename):
        print(f'while previewing media, {filename} : does not exist')
        flask.abort(404)
    return flask.send_file(filename)

@app.route('/update_stats')
def update_stats():
    data_manager.update_stats()
    return flask.redirect('/settings')

@app.route('/favicon.ico')
def favicon():
    return flask.send_file(f'{prefix}/static/favicon.ico')

@app.route('/bulk_edit', methods=['POST'])
def bulk_edit():
    global dataset_path
    pagechange()
    all_args = flask.request.form.to_dict()
    data = all_args.get('data')
    
    try:
        data = data.split('&')
        data = {entry.split(':')[0] : entry.split(':')[1] for entry in data}
        deletes = data.get('delete')
        if deletes != None:
            deletes = deletes.strip('[').strip(']')
            deletes = [x.strip() for x in deletes.split(',')]
        assert '' not in deletes
    except Exception as e:
        print(f'error parsing bulk edit data: {e}')
        flask.flash('Error parsing bulk edit data', 'error')
        return flask.redirect(r'/')

    #delete selected
    for post in deletes:
        data_manager.delete_post(post)
    return flask.redirect(r'/')

@app.route("/prev/<post_name>", methods=['GET', 'POST'])
def prev(post_name):
    global posts_per_page, dataset_path
    pagechange()
    all_args = flask.request.args.to_dict()
    page = int(all_args.get('page', 0))
    search = {key : value.replace(' ', '+') for key, value in all_args.items()}
    parent_href=search["search"]
    if not 'tags' in parent_href:
        tags=None
    else:
        tags = [parent_href.split('?')[-1].strip("'*'").split('tags=')[-1]]
    all_post_data, passed_ids = search_func(page, tags)

    if '_' not in post_name:
        return flask.abort(404)
    ind = max(0,passed_ids.index(post_name)-1)
    post = passed_ids[ind]
    return flask.redirect(f'/posts/{post}?parent_href={parent_href}')
    
@app.route("/next/<post_name>", methods=['GET', 'POST'])
def next(post_name):
    global posts_per_page, dataset_path
    pagechange()
    all_args = flask.request.args.to_dict()
    page = int(all_args.get('page', 0))
    search = {key : value.replace(' ', '+') for key, value in all_args.items()}
    parent_href=search["search"]
    if not 'tags' in parent_href:
        tags=None
    else:
        tags = [parent_href.split('?')[-1].strip("'*'").split('tags=')[-1]]
    all_post_data, passed_ids = search_func(page, tags)

    if '_' not in post_name:
        return flask.abort(404)
    ind = max(0,passed_ids.index(post_name)+1)
    post = passed_ids[ind]
    return flask.redirect(f'/posts/{post}?parent_href={parent_href}')
    
#viewable views
@app.route('/')
@app.route('/posts')
def home():
    global posts_per_page, dataset_path
    messages = pagechange()
    all_args = flask.request.args.to_dict()
    page = int(all_args.get('page', 0))
    edit = all_args.get('edit', 0)
    search = {key : value.split(' ') for key, value in all_args.items()}
    tags = search.get('tags', None)
    if 'page' in search.keys():
        del search['page']
    if "edit" in search.keys():
        del search['edit']
    all_post_data, passed_ids = search_func(page, tags)

    pageinator_obj = paginator(search, passed_ids, page)

    passed_ids = passed_ids[page*posts_per_page :]

    passed_ids = passed_ids[:posts_per_page]
    tag_list, post_html_list = build_post_html(passed_ids, all_post_data)
    
    #make tag list
    tag_htmls = []
    for tag in tag_list:
        wiki_link = f'/wiki/{tag}'
        search_link = f'/posts?tags={tag}'
        tag_html =f'''
    <li>
        <a class="wiki-link" href={wiki_link}>?</a>
        <a class="search-link" href="{search_link}">{tag.replace('_', ' ')}</a>
    </li>
'''
        tag_htmls.append(tag_html)
    search = ' '.join([f'{" ".join(value)}' if key == "tags" else f'{key}:{" ".join(value)}' for key, value in search.items()])

    all_post_data = None
    return flask.render_template('home.html', tags = tag_htmls, posts = post_html_list, pageinator = pageinator_obj, search=search, edit=(int(edit)==1), messages = messages)#

@app.route('/wiki')
@app.route('/wiki/')
def wiki():
    pagechange()

    all_args = flask.request.args.to_dict()
    search = {x[0]:x[1] for x in all_args.items() if (x[0] in ['name', 'category'] and x[1] != '')}
    order = all_args.get('order', 'count')
    if order not in ['count', 'name', 'date']:
        order = 'count'
    update = int(all_args.get('update', 0))
    tag_dict_path = f'{dataset_path}/tag_dict.json'
    tag_dict = data_manager.read_json(tag_dict_path)
    if 'all' not in tag_dict.keys() or (update == 1):
        print('tag_dict not found, generating')
        data_manager.recount_tagdict(tag_dict)
        data_manager.update_stats()

    tag_dict = tag_dict['all']
    if 'description' in tag_dict.keys():
        del tag_dict['description']
    if order == 'count':
        tag_list = sorted(tag_dict, key=lambda x: tag_dict[x]['count'], reverse=True)
    elif order == 'name':
        tag_list = sorted(tag_dict, key=lambda x: x)
    elif order == 'date':
        tag_list = sorted(tag_dict, key=lambda x: tag_dict[x]['last_edit'], reverse=True)
    
    tag_htmls = []
    for tag in tag_list:#filters tags based on search
        tag = str(tag)

        post_status = post_checker.post_checker(tag_dict[tag], search)
        if post_status == 'Invalid operator':
            search = ''
        if post_status == False:
            continue
        else:
            if type(tag_dict[tag]) != dict:
                continue
            wiki_link = f'/wiki/{tag}'
            search_link = f'/posts?tags={tag}'
            tag_html =f'''
        <li>
            <a class="wiki-link" href={wiki_link}>?</a>
            <a class="search-link" href="{search_link}">{tag.replace('_', ' ')}</a>
            <span>{tag_dict[tag]['count']}</span>
        </li>
    '''
            tag_htmls.append(tag_html)
    return flask.render_template('wiki.html', tags = tag_htmls)

@app.route('/import', methods=['GET', 'POST'])
@app.route('/import/', methods=['GET', 'POST'])
def import_post():
    method = flask.request.method
    stage = flask.request.args.get("stage", "start")
    if stage == 'start':
        if method == 'GET':
            return flask.render_template('importstart.html')
    elif stage == 'define':
        if method == 'POST':
            #time.sleep(3)
            all_files = flask.request.files
            for key, file in all_files.items():
                filename = str(file.filename)
                if filename.strip() == "":
                    flask.flash('No file selected', 'error')
                    return flask.redirect("/import")
                filepath = f'{app.static_folder}/temp/{filename}'#this is right
                file.save(filepath)
            
            media = generate_media_html(filepath)
            return flask.render_template('importdefine.html', media = media, filepath = filepath, source = "")
        else:
            return flask.abort(404)
    elif stage == 'url':
        if method == 'POST':
            url = flask.request.form.get('upload[source]', '').strip()
            if not url:
                flask.flash('No URL provided', 'error')
                return flask.redirect("/import")
            
            print(f'importing from url: {url}')
            path = os.path.normpath(f'{app.static_folder}/temp/media/imports')
            id_html, media_downloaded, media_objs = importer.get_media_from_url(url, path+"\\")
            if media_downloaded == 0:
                flask.flash('No media found at the provided URL', 'error')
                return flask.redirect('/import')
            cleaned_media_objs = "\n".join([str(x) for x in media_objs])
            print(f'media downloaded from {url}: {cleaned_media_objs}')
            filepaths = [x["filepath"] for x in media_objs if x["filepath"] != None]
            medias = [generate_media_html(x) for x in filepaths]
            tags = importer.get_tags_from_url(url)
            labeled_media = [(i,
                            html,
                            media_objs[i]["source"],
                            media_objs[i]["media_data"].items() if media_objs[i]["media_data"] else None,
                            os.path.basename(media_objs[i]["filepath"])
                            ) for i, html in enumerate(medias)]
            if media_downloaded > 1:
                print(f'multiple media downloaded from {url}')
                return flask.render_template('importchoose.html', images = labeled_media, tags = tags, source=url)
            
            filepath = filepaths[0]
            video_duration = importer.get_mediadata_info(filepath).get("length", 0)
            media_type = "video" if video_duration > 0 else "image"
            media_data = {"media_html" : medias[0], "media_type": media_type, "filepath":filepath, "tags" : tags, "source":url, "video_duration": video_duration}
            return flask.render_template('importdefine.html', media_data=media_data)
        else:
            return flask.abort(404)
    elif stage == 'choose':#destination after choosing a media obj. make sure /temp/media/imports is deleted afterwards
        all_args = flask.request.form.to_dict()
        image = all_args.get('image', 0)
        tags = all_args.get('tags', "")
        url = all_args.get('source', "")
        all_images = os.listdir(f'{app.static_folder}/temp/media/imports')
        try:
            filepath = f'{app.static_folder}/temp/media/imports/' + image
            os.chmod(filepath, 0o644)  # make sure the file is readable
            data_manager.clean_temp(whitelist = [filepath])
        except (ValueError, IndexError):
            flask.flash(f'Error: Invalid image selection {image}. Please choose a valid image.', 'error')
            print(f'error choosing image: {image} not in {all_images}')
            data_manager.clean_temp()
            return flask.redirect('/import')

        media = generate_media_html(filepath)
        video_duration = importer.get_mediadata_info(filepath).get("length", 0)
        media_type = "video" if video_duration > 0 else "image"
        media_data = {"media_html" : media, "media_type": media_type, "filepath":filepath, "tags" : tags, "source":url, "video_duration": video_duration}
        return flask.render_template('importdefine.html', media_data=media_data)
    elif stage == 'submit':
        #get post details
        global dataset_path
        all_args = flask.request.args
        tags = all_args.get('tags', "").split(" ")
        original_source = all_args.get('source', "")
        rating = all_args.get('rating', "")
        title = all_args.get('title', "")
        filepath = all_args.get('filepath', "")
        site = all_args.get('site', "homebooru")
        video_start = float(all_args.get('video_start', 0))
        video_end = float(all_args.get('video_end', None))

        post = classes.post()

        full_list = data_manager.read_json(f'{dataset_path}\master_list.json')
        if not site in full_list.keys():
            data_manager.create_site(site)
        id_list = [int(x) for x in full_list[site]]

        cleaned_tags = data_manager.tag_cleaner(tags)
        post_id = max(id_list)+1
        mediadata_info = importer.get_mediadata_info(filepath, original_source=original_source)
        new_filepath = f'{dataset_path}/homebooru/media/{post_id}.{mediadata_info["file_extenstion"]}'
        data_manager.move_file(filepath, new_filepath)
        post_data = {#mutables first
            'id': f'{site}_{post_id}',
            'tags': cleaned_tags,
            'title': title,
            'rating': rating,
            'mediadata' : mediadata_info,
            'time_catalouged' : round(time.time(),2),
            'uploader_id': '001',
            'uploader_name': "yours turly",
            'score': None,
            'storage_path': new_filepath
        }
        #add post info
        post.from_json(post_data)
        data_manager.create_post(post)
        data_manager.clean_temp(whitelist = [new_filepath])
        data_manager.recode_video(new_filepath, video_start, video_end)

        return flask.redirect(f'/posts/homebooru_{post_id}')

def generate_media_html(filepath):
    media_info = importer.get_mediadata_info(filepath)
    if media_info is None:
        print(f'error generating media html for {filepath}')
        return ''
    width = media_info['media_width']
    height = media_info['media_height']
    if width*height <=1:
        image_dimensions = ""
    else:
        image_dimensions = f'width="{width}" height="{height}"'
    filename = re.sub('\\'+'\\', '/', filepath)
    img_path = flask.url_for('preview', filename = filename, mode = 'preview')
    media = f'''
    <picture>   
        <source srcset="{ img_path }">
        <img class="resized-media centered image preview" src="{ img_path }" id="post-media" {image_dimensions} >
    </picture>
    '''

    return media

#mutable pages
@app.route('/posts/<post_name>', methods=['GET', 'POST'])
def post_page(post_name):
    if '_' not in post_name:
        return flask.abort(404)
    post_site, post_id = post_name.split('_')
    log_location = f'{dataset_path}/{post_site}/post_data.json'
    full_data = data_manager.read_json(log_location)
    post_data = dict(full_data[post_id])
    post_data['id'] = post_name
 
    all_args = parse_args()
    edit = int(all_args.get('edit', 0)) #0=nothing, 1=enter details, 2=process edit 
    delete = int(all_args.get('delete', 0)) #0=nothing, 1=confirm, 2=process delete 
    rank = all_args.get('rank', None)
    parent_href = all_args.get('parent_href', None)
    pagechange()
    
    if delete == 2:
        print(parent_href)
        
        print('end parent href:', parent_href)
        data_manager.delete_post(post_name)
        return flask.redirect(parent_href)

    if rank != None:
        rank = int(rank)
        if 'rank' not in post_data.keys():
            post_data.update({'rank':rank})
        else: 
            post_data['rank'] = rank
        full_data[post_id] = post_data  
        data_manager.write_json(log_location, full_data)

    #load post
    img_path = flask.url_for('preview', filename=re.sub('\\'+'\\', '/', post_data["storage_path"]))
    if post_data["title"] == '': 
        title = post_name
    else:
        title = str(post_data["title"])
        title = title.replace('_', ' ')  
    width = post_data['mediadata']['media_width']
    height = post_data['mediadata']['media_height']
    if width*height <=1:
        image_dimensions = ""
    else:
        image_dimensions = f'width="{width}" height="{height}"'
    file_ext = post_data["storage_path"].split('.')[-1]
    if (post_data['mediadata']['length'] > 1) and (file_ext != 'gif'):
        media = f'''
    <video controls loop class="resized-media"src="{img_path}" {image_dimensions} id="post-media">
    </video>
    '''
    else:
        media = f'''
    <picture>
        <source srcset="{ img_path }">
        <img class="resized-media" src="{ img_path }" id="post-media" {image_dimensions} >
    </picture>
    '''
  
    ending = ''

    if delete == 1:
        ending += f'''
<h2> DELETE POST {post_name}? </h2>
    <a href="/posts/{post_name}?delete=2" name="link-to-self">DELETE</a>
                          '''
    tag_htmls, other_postdata_html = format_post_data(post_data)

    if edit == 1:
        catagories = [f'''
            <label for="{catagory}">{catagory}</label> <br> 
            <textarea class="tag-textarea selector {"large-selector" if catagory == "tags" else ""}" name="{catagory}">{" ".join(post_data[catagory]) if is_iterable(post_data[catagory]) else str(post_data[catagory])}</textarea>'''
        for catagory in post_data if catagory not in immutables]

        ending += f'''
    <h2>Edit</h2>
    <form action="/posts/{post_name}?edit=2" method="post">
        {
            "<br>".join(catagories)
        }
        <br>
        <input type="submit" value="Submit">
    </form>
    '''
    elif edit == 2:
        data = flask.request.form.to_dict()
        for key in data:
            if key in immutables:
                continue
            else:
                if ((' ' in data[key]) and (type(data[key]) == str)):
                    data[key] = sorted(set(data[key].split(' ')))
                post_data[key] = data[key]
        post_data["tags"] = data_manager.tag_cleaner(post_data["tags"])
        full_data[post_id] = post_data
        data_manager.write_json(log_location, full_data)
        return flask.redirect(f'/posts/{post_name}')

    return flask.render_template('post.html', title = title, tag_list = tag_htmls, info = other_postdata_html , media = media, edit = ending)

@app.route('/wiki/<tag>', methods=['GET', 'POST'])
def wiki_page(tag):
    pagechange()
    title = f'homebooru wiki: {tag}'
    href = f'/wiki/{tag}?create=True'

    all_args = flask.request.args.to_dict()
    create = bool(all_args.get('create', False))
    tag_dict = data_manager.read_json(f'{dataset_path}/tag_dict.json')
    edit = int(all_args.get('edit', 0)) #0=nothing, 1=enter details, 2=process edit 

    #print(tag_dict)
    tag_data = tag_dict["all"].get(tag, None)
    if tag_data == None:
        content = f'tag not found <a href ="{href}">create one?</a>'
    else:
        #print(tag_data)
        tag_obj = classes.tag()
        tag_data = tag_obj.format_dict(tag_data)
        if create:
            pass
        
        desc = tag_data.get("description", "no description yet")
        if desc == "": desc = "no description yet"
        count = tag_data.get("count", 0)
        last_updated = tag_data.get("last_updated", 0)
        robots = tag_data.get("robots", {"no robots yet":0})

    similar_tags = []
    for new_tag in tag_dict["all"].values():
        if type(new_tag) != dict:
            continue
        is_similar = post_checker.post_checker(new_tag, {'name' : f'{tag}~'})
        if is_similar: similar_tags.append(new_tag['name'])
    similar_tags.remove(tag)

    ending =''
    if edit == 1:
        catagories = []
        for catagory in robots:
            if catagory in immutables:
                continue
            elif catagory in ['aliases', 'implications', 'replace']:
                catagories.append(f'''
            <label for="{catagory}">{catagory}</label> <br> 
            <textarea class="tag-textarea" name="{catagory}">{" ".join([str(x) for x in robots[catagory]]) if is_iterable(robots[catagory]) else str(robots[catagory])}</textarea>''')
            else:
                catagories.append(f'''
            <input type="checkbox" name="{catagory}" id="{catagory}" value="true">
            <label for="{catagory}">{catagory}</label>
                ''')


        ending += f'''
    <h2>Edit</h2>
    <form action="/wiki/{tag}?edit=2" method="post">
        <label for="description"><h3> Description </h3></label>
        <textarea class="tag-textarea" name="description">{desc}</textarea>
        <h3> Robots </h3>
        {"<br>".join(catagories)}
        <br><br>
        <input type="submit" value="Submit">
    </form>
    '''
        
    elif edit == 2:
        #update entry
        data = flask.request.form.to_dict()
        for key in data:
            if key in immutables:
                continue
            else:
                if (key in ['aliases', 'implications', 'replace', 'remove']):
                    tag_data['robots'][key] = sorted(set(data[key].split(' ')))
                else:
                    tag_data[key] = data[key]
        tag_dict["all"][tag] = tag_data
        data_manager.write_json(f'{dataset_path}/tag_dict.json', tag_dict)
        #update posts
        robots = tag_data['robots']
        data_manager.update_wiki(tag, robots)

        return flask.redirect(f'/wiki/{tag}')

    content = {
        "count" : count,
        'last_updated': last_updated,
        'tag': tag,
        'desc': desc,
        'robots': robots,
        'similar_tags': similar_tags
        }
    return flask.render_template('wikipost.html', title = title, data = content, ending = ending)

@app.route('/settings')
@app.route('/settings/')
def settings():
    stats = data_manager.read_json(f'{dataset_path}/stats.json')
    return flask.render_template('settings.html', stats = stats)

if __name__ == '__main__':
    global server
    port = data_manager.get_setting('port')
    port = 1741
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    data_manager.create_all()
    print(f"Server started on {hostname} at {ip_address}:{port}")
    app.secret_key = 'supersecretkey'
    app.run(debug=True, host='0.0.0.0', port=port)
