function resize_check(){
    const media = document.getElementById("post-media");
    const resize_bool = Boolean( new URLSearchParams(window.location.search).get("resize"));
    if (resize_bool == true) {
        media.classList.remove("resized-media")
    }
    console.log(`curr height ${media.offsetHeight} orig height ${media.naturalHeight}`)
    console.log(`curr width ${media.offsetWidth} orig width ${media.naturalWidth}`)
    const resize_notice = document.getElementById("image-resize-notice");
    if (media.naturalHeight != undefined || media.naturalWidth != undefined){
        var resize_amount = Math.round(Math.max(Math.min(media.offsetHeight/media.naturalHeight, 1), Math.min(media.offsetWidth/media.naturalWidth, 1))*100);
    }
    else {
        var resize_amount = 100
    }
    resize_notice.childNodes[0].nodeValue = 'resized to ' + String(resize_amount) + '% ';
    console.log('resize_amount: '+resize_amount)
    if (resize_amount <= 98) {
        resize_notice.hidden = false;
    }
}

function add_parentlink(element_array) {
    const web_path = window.location.href;
    if (web_path.includes('parent_href=')) {

        var parent_href = web_path.match(".*?parent_href=%27%27%27(.*?)%27").at(-1);
    }
    else {
        var parent_href = web_path;
    }

    element_array.forEach(element => {
        if (web_path.includes('parent_href=')) {
            //console.log(element + ' path 1');
            element.href = element.href + "&parent_href='''" + parent_href +"'*'";
            return;
        }
        if (element.href.includes('?')) {
            //console.log(element + ' path 2')
            element.href = element.href + "&parent_href='''" + web_path +"'*'"
        }
        else {
            //console.log(element + ' path 3')
            element.href = element.href + "?parent_href='''" + web_path +"'*'"
        }
    });
    return parent_href
}