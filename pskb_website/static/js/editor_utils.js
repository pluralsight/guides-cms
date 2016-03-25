var editor;
var author_name;
var author_real_name;

// Returns a function, that, as long as it continues to be invoked, will not
// be triggered. The function will be called after it stops being called for
// N milliseconds. If `immediate` is passed, trigger the function on the
// leading edge, instead of the trailing.
function debounce(func, wait, immediate) {
    var timeout;
    return function() {
        var context = this, args = arguments;
        var later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        var callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
};

var previewUpdated = debounce(function() {
    var header = get_article_header_data();
    var content_as_markdown = header + '\n' + editor.getSession().getValue();
    var content_as_html = marked(content_as_markdown);
    var preview = $('#preview');
    preview.html(content_as_html);
    $('pre code').each(function(i, e) {hljs.highlightBlock(e)});
}, 200);

function initialize_editor(local_filename, content, name, real_name, img_upload_url) {
    author_name = name;
    author_real_name = real_name;

    editor = ace.edit("editor");
    editor.setTheme("ace/theme/github");
    editor.getSession().setMode("ace/mode/markdown");
    editor.getSession().setUseWrapMode(true);
    // editor.getSession().setNewLineMode("unix");
    editor.setShowPrintMargin(false);
    editor.setOption('maxLines', 99999);
    // editor.renderer.setShowGutter(false);
    // editor.renderer.setOption('showLineNumbers', false);

    var placeholder = "\n\
# Markdown tutorial by example\
\n\n\
Read this if you need to check the Markdown syntax. Otherwise, erase this text and start writing your guide.\
\n\n\
# Headers \
\n\n\
## Header's Subsection \
\n\n\
### Header's Subsection \
\n\n\
#### Header's Subsection \
\n\n\
##### Header's Subsection \
\n\n\
# Text Format \
\n\n\
normal, *italic*, **bold**, __bold__, _emphasis_, ùníçõd&, `code`, \*escaping special chars\*, &copy; \
\n\n\
## Bloquote \
\n\n\
> You can put some warning or important messages in bloquotes. \n\
Check that a bloquote can have multiple lines. \
\n\n\
# Code \
\n\n\
```\n\
print('test')\n\
```\
\n\n\
```javascript\n\
$(function(){\n\
  $('div').html('I am a div.');\n\
});\n\
```\
\n\n\
### Lists\
\n\n\
#### Unordered list\
\n\n\
- item 1\n\
- item 2\n\
\n\
or\n\
\n\
* item 1\n\
* item 2\
\n\n\
#### Ordered list\
\n\
1. item 1\n\
1. item 2\n\
\n\
or\n\
\n\
1. item 1\n\
2. item 2\n\
\n\
### Links\
\n\n\
* [text of the link](http://hackguides.org)\n\
* http://hackguides.org\
\n\n\
### Images and Files\
\n\n\
![alt text](http://tutorials.pluralsight.com/static/img/dark-logo.png 'Logo Title')\
\n\n\
";
    editor.setValue(content || placeholder);
    editor.gotoLine(1);
    previewUpdated();

    editor.getSession().on('change', function(e) {
        previewUpdated();
    });

    configure_dropzone_area(img_upload_url);

    return editor;
}

var scrollSyncEnabled = false;
var $divs = null;
var scrollSyncFunction = function(e) {
    var
      $other     = $divs.not(this).off('scroll'),
      other      = $other[0],
      percentage = this.scrollTop / (this.scrollHeight - this.offsetHeight);

    other.scrollTop = Math.round(percentage * (other.scrollHeight - other.offsetHeight));

    setTimeout(function() { $other.on('scroll', scrollSyncFunction); }, 10);

    return false;
};

function toggleScrollSync() {
    $divs = $('#editor-wrapper, #preview');
    if (scrollSyncEnabled) {
        $divs.off('scroll', scrollSyncFunction);
    } else {
        $divs.on('scroll', scrollSyncFunction);
    }
    scrollSyncEnabled = ! scrollSyncEnabled;
}

function configure_dropzone_area(img_upload_url) {
    Dropzone.autoDiscover = false;
    var dropZoneOptions = {
        url: img_upload_url,
        paramName: 'file',
        maxFilesize: 3, // MB
        uploadMultiple: false,
        disablePreview: false,
        createImageThumbnails: false,
        addRemoveLinks: false,
        previewTemplate: document.querySelector('#preview-template').innerHTML,
        clickable: '.btn-dropzone',
        accept: function(file, done) {
            if (file.name.endsWith('.exe') || file.name.endsWith('.bin') || file.name.endsWith('.bat')) {
                done("File not supported");
            }
            else {
                done();
            }
        }
    };
    var myDropzone = new Dropzone("div#droppable-area", dropZoneOptions);
    myDropzone.on('success', function(file, path) {
        // Add Markdown reference into the editor
        var fileMarkdown = '\n![description](' + path + ')\n';
        editor.insert(fileMarkdown);
    });

    myDropzone.on("complete", function(file) {
        myDropzone.removeFile(file);
    });

    return myDropzone;
}

function get_article_header_data() {
    var title = document.getElementById('title').value;

    var h1 = '<h1 id="title" class="tagline gradient-text" style="margin-top: 5px">' + title + '</h1>';
    var h4 = '<h4 id="author"><small>written by ';

    var anchor = '<a href="#">';
    if (author_name != undefined && author_name != '') {
        anchor = '<a href="/user/"' + author_name + '>';
    }

    if (author_real_name != undefined && author_real_name != '') {
        anchor += author_real_name;
    } else if (author_name != undefined && author_name != '') {
        anchor += author_name;
    } else {
        anchor += 'you';
    }

    anchor += '</a>';
    h4 += anchor + '</small></h4>';
    var selected_stacks = document.getElementById('stacks').selectedOptions;
    var stacks = '';
    for (ii = 0; ii < selected_stacks.length; ii++) {
        if (selected_stacks[ii].value != '') {
            stacks += selected_stacks[ii].value + ',';
        }
    }

    if (stacks.length) {
        if (stacks[stacks.length - 1] == ',') {
            stacks = stacks.slice(0, -1);
        }
    }

    var h5 = '<h5 id="related"><small>Related to ' + stacks + '</small>';
    var header = '<div class="header">' + h1 + h4 + h5 + '</div>' + '<hr>';

    return header;
}


function save(sha, path, secondary_repo, action_url) {
    var form = document.createElement("form");
    form.action = action_url;
    form.method = "POST";

    var textarea = document.createElement("textarea");
    textarea.name = "content";
    $(textarea).val(editor.getSession().getValue());
    form.appendChild(textarea);

    var sha_elem = document.createElement("input");
    sha_elem.name = "sha";
    sha_elem.value = sha;
    form.appendChild(sha_elem.cloneNode());

    var path_elem = document.createElement("input");
    path_elem.name = "path";
    path_elem.value = path;
    form.appendChild(path_elem.cloneNode());

    var title = document.getElementById("title");
    form.appendChild(title.cloneNode());

    var orig_stack = document.getElementById("original_stack");
    form.appendChild(orig_stack.cloneNode());

    var stacks_select = document.getElementById("stacks");
    var stacks = document.createElement("input");
    stacks.name = "stacks";
    stacks.value = stacks_select.value;
    form.appendChild(stacks.cloneNode());

    if (secondary_repo) {
        var secondary_repo_elem = document.createElement("input");
        secondary_repo_elem.name = "secondary_repo";
        secondary_repo_elem.value = 1;
        form.appendChild(secondary_repo_elem.cloneNode());
    }

    // To be sent, the form needs to be attached to the main document.
    form.style.display = "none";
    document.body.appendChild(form);

    form.submit();

    // But once the form is sent, it's useless to keep it.
    document.body.removeChild(form);
}
