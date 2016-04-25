var MARKDOWN_TUTORIAL = "\
# Markdown tutorial by example\
\n\n\
Read this if you need to check the Markdown syntax. \n\n\
\
> **Disable the live tutorial to go back to your article**.\n\
\
\n\n\n\
# Headers \
\n\n\
## Header's Subsection \
\n\n\
### Header's Subsection \
\n\n\
#### Header's Subsection \
\n\n\
##### Header's Subsection \
\n\n\n\
# Text Format \
\n\n\
normal, *italic*, **bold**, __bold__, _emphasis_, ~~strikethrough~~, ùníçõd&, `code`, \*escaping special chars\*, &copy; \
\n\n\
## Bloquote \
\n\n\
> You can put some warning or important messages in blockquotes. \n\
Check that a blockquote can have multiple lines. \
\n\n\n\
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
\n\n\n\
# Lists\
\n\n\
## Unordered list\
\n\n\
- item 1\n\
- item 2\n\
\n\
or\n\
\n\
* item 1\n\
* item 2\
\n\n\
## Ordered list\
\n\n\
1. item 1\n\
1. item 2\n\
\n\
or\n\
\n\
1. item 1\n\
2. item 2\n\
\n\
## Nesting\
\n\n\
1. item 1\n\
  1. item 1.1\n\
  2. item 1.2\n\
    - subitem 1\n\
    - subitem 2\n\
2. item 2\n\
\n\
## Task Listing\
\n\n\
- [ ] item 1\n\
- [x] item 2\n\
\n\n\
# Tables\
\n\n\
First Column Header | Second Column Header | Third Column\n\
------------------- | -------------------- | ------------\n\
Content from cell 1 | | Content from cell 3\n\
Another cell 1 | Another cell 2\n\
\n\n\
# Links\
\n\n\
* [text of the link](http://hackguides.org)\n\
* http://hackguides.org\
\n\n\n\
# Images and Files\
\n\n\
![alt text](http://tutorials.pluralsight.com/static/img/dark-logo.png 'Logo Title')\
\n\n\n\
# Horizontal rules\
\n\n\
------------------------\
\n\n\
or\
\n\n\
* * *\
\n\n\
or\
\n\n\
*****\
\n\n\
";

var editor;
var author_name;
var author_real_name;
var current_local_filename;
var help_sections;
var isHelpEnabled = true;

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
    var content_as_markdown = editor.getSession().getValue();
    var content_as_html = marked(content_as_markdown);
    var preview = $('#preview');
    preview.html(content_as_html);

    /* From utils.js */
    create_external_links('#preview');

    $('pre code').each(function(i, e) {hljs.highlightBlock(e)});
}, 500);

var autosaveEnabled = true;

var loadAutoSave = function(local_filename) {
    var obj = localStorage.getItem('hack.guides');
    if (obj) {
        obj = JSON.parse(obj);
        return obj[local_filename]; // markdown content or undefined
    }
    return undefined;
}

var autoSave = debounce(function(local_filename) {
    var content_as_markdown = editor.getSession().getValue();
    var obj = localStorage.getItem('hack.guides') || '{}';
    obj = JSON.parse(obj);
    obj[local_filename] = content_as_markdown;
    localStorage.setItem('hack.guides', JSON.stringify(obj));
}, 1000);

var clearLocalSave = function(local_filename) {
    var obj = localStorage.getItem('hack.guides');
    if (obj) {
        obj = JSON.parse(obj);
        delete obj[local_filename];
        localStorage.setItem('hack.guides', JSON.stringify(obj));
    }
    return undefined;
}

function initialize_editor(local_filename, content, name, real_name, img_upload_url) {
    author_name = name;
    author_real_name = real_name;
    current_local_filename = local_filename;

    editor = ace.edit("editor");
    editor.setTheme("ace/theme/github");
    editor.getSession().setMode("ace/mode/markdown");
    editor.getSession().setUseWrapMode(true);
    // editor.getSession().setNewLineMode("unix");
    editor.setShowPrintMargin(false);
    editor.setOption('maxLines', 99999);
    editor.$blockScrolling = Infinity;
    // editor.renderer.setShowGutter(false);
    // editor.renderer.setOption('showLineNumbers', false);

    toggleFullscreenMode();

    marked.setOptions({
      gfm: true,
      tables: true,
      breaks: true,
      pedantic: false,
      sanitize: false,
      smartLists: true,
      smartypants: false
    });

    var placeholder = '# Start writing your guide here.\n\nOr load the live markdown tutorial to check the syntax.';
    var local_content = loadAutoSave(local_filename);
    // local content should always be the same or the most updated version.
    editor.setValue(local_content || content || placeholder);
    editor.gotoLine(1);
    previewUpdated();

    if (content && ! local_content) {
        autoSave(local_filename);
    }

    editor.getSession().on('change', function(e) {
        previewUpdated();
        if (autosaveEnabled) {
            autoSave(local_filename);
        }
    });

    configure_dropzone_area(img_upload_url);

    return editor;
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

function openLiveMarkdownTutorial() {
    autosaveEnabled = false;
    editor.getSession().setValue(MARKDOWN_TUTORIAL);
    $('.btn-save').prop('disabled', true);
}

function closeLiveMarkdownTutorial() {
    editor.setValue(loadAutoSave(current_local_filename) || '');
    autosaveEnabled = true;
    $('.btn-save').prop('disabled', false);
}

var liveTutorialEnabled = false;
function toggleLiveTutorial() {
    if (liveTutorialEnabled) {
        closeLiveMarkdownTutorial();
    } else {
        openLiveMarkdownTutorial();
    }
    liveTutorialEnabled = ! liveTutorialEnabled;
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

var isFullscreenEnabled = false;

function closeFullscreen() {
    $('html, body').removeClass('body-fs');
    isFullscreenEnabled = false;
    show_all_help_sections(true);
}

function openFullscreen() {
    $('html, body').addClass('body-fs');
    isFullscreenEnabled = true;
}

function toggleFullscreenMode() {
    if (isFullscreenEnabled) {
        closeFullscreen();
    } else {
        openFullscreen();
    }
}

var clearFlashMessages = function(message, clazz) {
    $('.bg-info, .bg-warning, .bg-danger').remove();
};

var addFlashMessage = function(message, clazz) {
    var msg = '<p class="' + (clazz || 'bg-info') + '">' + message + '</p>';
    $('.flash-msgs').append(msg);
};

function save(sha, path, secondary_repo) {
    clearFlashMessages();
    $('.btn-save').prop('disabled', true);
    var data = {
        'title': $('input[name=title]').val(),
        'original_stack': $('input[name=original_stack]').val(),
        'stacks': $('#stacks').val(),
        'content': editor.getSession().getValue(),
        'sha': sha,
        'path': path
    }
    if (secondary_repo) {
        data['secondary_repo'] = 1;
    }
    $.ajax({
        type: 'POST',
        url: '/api/save/',
        contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
        data: data,
        dataType: 'json',
        cache: false,
        beforeSend: function(xhr) {
            $('html, body').css("cursor", "wait");
            return true;
        },
        complete: function(xhr, txt_status) {
            $('html, body').css("cursor", "auto");
        },
        success: function(data) {
            closeFullscreen();
            console.log(data);
            console.log(data.msg);
            clearLocalSave(current_local_filename);
            if (data.msg) {
                addFlashMessage(data.msg);
                $("html, body").animate({ scrollTop: 0 }, "fast");
                $('.btn-save').prop('disabled', false);
            }
            setTimeout(function(){ window.location.href = data.redirect; }, 1000);
        },
        error: function(response) {
            closeFullscreen();
            var status = response.status;
            var data = response.responseJSON;
            console.log(status, data);
            if (data && data.error) {
                addFlashMessage(data.error, 'bg-danger');
                $("html, body").animate({ scrollTop: 0 }, "fast");
                $('.btn-save').prop('disabled', false);
            }
            if (data && data.redirect) {
                setTimeout(function(){ window.location.href = data.redirect; }, 1000);
            } else {
                $('.btn-save').prop('disabled', false);
            }
        },
    });
}

function visible_section_idx() {
    for (var ii=0; ii < help_sections.length; ii++) {
        if ($(help_sections[ii]).css('display') == 'block') {
            return ii;
        }
    }

    return -1;
}

function goto_section(next_section) {
    for (var ii=0; ii < help_sections.length; ii++) {
        if (next_section == ii ) {
            $(help_sections[ii]).css('display', 'block');
        } else {
            $(help_sections[ii]).css('display', 'none');
        }
    }
}


function show_all_help_sections(should_show) {
    var display = 'none';
    if (should_show) {
        display = 'block';
    }

    for (var ii=0; ii < help_sections.length; ii++) {
        $(help_sections[ii]).css('display', display);
    }
}

function toggleHelp() {
    if (isHelpEnabled) {
        hideHelp();
    } else {
        showHelp();
    }
}


function showHelp() {
    $('#editor-help').fadeIn('fast');
    $('#editor-help').show();
    isHelpEnabled = true;
}

function hideHelp() {
    $('#editor-help').fadeOut('fast');
    $('#editor-help').hide();
    isHelpEnabled = false;
}


/* Show each section 1 at a time in help. This only works for full-screen mode
 * because these buttons are visible otherwise. */
function init_editor_help() {
    help_sections = $('#editor-help').find('.section');
    goto_section(0);

    $('#editor-help #next').click(function() {
        var curr_section = visible_section_idx();
        var next_section = curr_section + 1;

        if (next_section >= help_sections.length) {
            next_section = 0;
        }

        goto_section(next_section);
    });

    $('#editor-help #prev').click(function() {
        var curr_section = visible_section_idx();
        var next_section = curr_section - 1;

        if (next_section < 0) {
            next_section = help_sections.length - 1;
        }

        goto_section(next_section);
    });
}
