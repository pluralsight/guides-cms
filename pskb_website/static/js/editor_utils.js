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

// Article data
var editor;
var author_name;
var author_real_name;
// Auto-save
var current_local_filename;
var autosaveEnabled = true;
// Preview
var preview = null;
var editor_wrapper = null;
var updatingPreview = false;
// Markdown tutorial
var liveTutorialEnabled = false;
// Scroll Sync
var scrollSyncEnabled = false;
// Virtual DOM
var vdom = window.virtualDom;
var html2vtree = window.vdomParser;
var currentVTree = null;
var previewRootDomNode = null;

var help_sections;
var isHelpEnabled = false;

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
        if (_.isFunction(wait)) {
            timeout = setTimeout(later, wait());
        } else {
            timeout = setTimeout(later, wait);
        }
        if (callNow) func.apply(context, args);
    };
};

function getUpdatePreviewDelay() {
    var delay = 0;
    var cursorLine = editor.selection.getCursor()['row'];
    var totalOfLines = editor.session.getLength();
    var linesAfterCursor = totalOfLines - cursorLine;
    if (linesAfterCursor > 2000) {
        delay = 2000 - 200;
    } else if (linesAfterCursor > 1000) {
        delay = 1000 - 200;
    } else if (linesAfterCursor > 500) {
        delay = 500 - 200;
    }
    return delay;
}

var highlightNewCode = function(patches) {
    var codesPatched = [];
    Object.keys(patches).forEach(function (key) {
        if ( 'a' === key ) {
        } else if ( Array.isArray(patches[key]) ) {
            patches[key].forEach(function (vpatch, ii) {
                var node = vpatch.vNode || vpatch.patch;
                var tagExists = node && node.tagName;
                var tagName = tagExists && node.tagName.toUpperCase();
                if (tagExists && (tagName == 'PRE')) {
                    codesPatched.push(node.key);
                }
            })
        }
        else {
            var vpatch = patches[key];
            var node = vpatch.vNode || vpatch.patch;
            var tagExists = node && node.tagName;
            var tagName = tagExists && node.tagName.toUpperCase();
            if (tagExists && (tagName == 'PRE')) {
                codesPatched.push(node.key);
            }
        }
    });
    codesPatched.forEach(function (key, i) {
        var elem = $('pre[data-id="' + key + '"]')[0];
        if (elem) { // element may be removed
            hljs.highlightBlock(elem);
        }
    });
}

var updatePreview = function() {
    if (updatingPreview) {
        return;
    }
    updatingPreview = true;

    var newHtml = markdown2html(editor.getSession().getValue());
    newVTree = html2vtree('<div class="previewWrapper markdown-body" key="previewWrapper">' + newHtml + '</div>', 'key');

    if (! currentVTree) {
        currentVTree = newVTree;
        try {
            previewRootDomNode = vdom.create(currentVTree);
        } catch(err) {
            console.error(err);
            previewRootDomNode = null;
            currentVTree = null;
            updatingPreview = false;
            return;
        }
        preview.appendChild(previewRootDomNode);
        $(preview).find('pre code').each(function(i, e) {
            hljs.highlightBlock(e);
        });
    }

    var patches = vdom.diff(currentVTree, newVTree);
    var numberDiffNodes = Object.keys(patches).length - 1;
    if (numberDiffNodes > 0) {
        try {
            previewRootDomNode = vdom.patch(previewRootDomNode, patches);
        } catch(err) {
            console.error(err);
            previewRootDomNode = null;
            currentVTree = null;
            updatingPreview = false;
            return;
        }
        currentVTree = newVTree;
        highlightNewCode(patches);
        scrollPreviewAccordingToEditor();
    }
    updatingPreview = false;
};


var loadAutoSave = function(local_filename) {
    var obj = localStorage.getItem('hack.guides');
    if (obj) {
        obj = JSON.parse(obj);
        return obj[local_filename]; // markdown content or undefined
    }
    return undefined;
}

var autoSave = function(local_filename) {
    var content_as_markdown = editor.getSession().getValue();
    var obj = localStorage.getItem('hack.guides') || '{}';
    obj = JSON.parse(obj);
    obj[local_filename] = content_as_markdown;
    localStorage.setItem('hack.guides', JSON.stringify(obj));
};

var clearLocalSave = function(local_filename) {
    var obj = localStorage.getItem('hack.guides');
    if (obj) {
        obj = JSON.parse(obj);
        delete obj[local_filename];
        localStorage.setItem('hack.guides', JSON.stringify(obj));
    }
    return undefined;
}

function initialize_editor(local_filename, name, real_name, img_upload_url) {
    author_name = name;
    author_real_name = real_name;
    current_local_filename = local_filename;

    preview = document.getElementById('preview');
    editor_wrapper = document.getElementById('editor-wrapper');

    editor = ace.edit("editor");
    editor.setTheme("ace/theme/github");
    editor.getSession().setMode("ace/mode/markdown");
    editor.getSession().setUseWrapMode(true);
    editor.getSession().setNewLineMode("unix");
    // Manage editor size
    editor.setOption('minLines', 1);
    $(window).resize(resizeEditor);
    resizeEditor();
    editor.$blockScrolling = Infinity;
    // Editor layout features
    editor.setShowPrintMargin(false);
    editor.renderer.setShowGutter(true);
    editor.renderer.setOption('showLineNumbers', true);

    var content = $('#__initial_content__').val();
    $('#__initial_content__').remove();
    var placeholder = '# Start writing your guide here.\n\nOr load the live markdown tutorial to check the syntax.';
    var local_content = loadAutoSave(local_filename);
    // local content should always be the same or the most updated version.
    editor.setValue(local_content || content || placeholder);
    editor.gotoLine(1);
    updatePreview();

    if (content && ! local_content) {
        autoSave(local_filename);
    }

    editor.getSession().on('change', debounce(updatePreview, getUpdatePreviewDelay));
    editor.getSession().on('change', debounce(function() {
        if (autosaveEnabled) {
            autoSave(local_filename);
        }
    }, 2000));


    editor.getSession().on('changeScrollTop', function(scrollTop) {
        scrollPreviewAccordingToEditor(scrollTop);
    })

    configure_dropzone_area(img_upload_url);

    return editor;
}

function getAceEditorScrollHeight() {
    var r = editor.renderer;
    return r.layerConfig.maxHeight - r.$size.scrollerHeight + r.scrollMargin.bottom;
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
    liveTutorialEnabled = true;
    autosaveEnabled = false;
    editor.getSession().setValue(MARKDOWN_TUTORIAL);

    $('.tutorial-title, #btn-close').show();
    $('#article-title, #article-stack, #title, #stacks').hide();
    $('[data-id="stacks"]').parent().hide();
    $('#btn-save, #btn-back').hide();

    $("#btn-live-tutorial").addClass('active');
}

function closeLiveMarkdownTutorial() {
    liveTutorialEnabled = false;
    editor.setValue(loadAutoSave(current_local_filename) || '');
    editor.gotoLine(1);
    autosaveEnabled = true;

    $('.tutorial-title, #btn-close').hide();
    $('#article-title, #article-stack, #title, #stacks').show();
    $('[data-id="stacks"]').parent().show();
    $('#btn-save, #btn-back').show();

    $("#btn-live-tutorial").removeClass('active');
}

function toggleLiveTutorial() {
    if (liveTutorialEnabled) {
        closeLiveMarkdownTutorial();
    } else {
        openLiveMarkdownTutorial();
    }
}

function scrollPreviewAccordingToEditor(scrollTop) {
    if (scrollSyncEnabled) {
        scrollTop = scrollTop || editor.session.getScrollTop();
        var editorHeight = getAceEditorScrollHeight();
        var percentage = scrollTop / editorHeight;

        // FIXME: Getting preview.scrollHeight and preview.offsetHeight is slow
        preview.scrollTop = Math.round(percentage * (preview.scrollHeight - preview.offsetHeight));
    }
}

function scrollEditorAccordingToPreview() {
    $(preview).off('scroll');

    var percentage = this.scrollTop / (this.scrollHeight - this.offsetHeight);

    var editorHeight = getAceEditorScrollHeight();
    var position = Math.round(percentage * editorHeight);
    editor.getSession().setScrollTop(position);

    setTimeout(function() { $(preview).on('scroll', scrollEditorAccordingToPreview); }, 10);
}

function toggleScrollSync() {
    if (scrollSyncEnabled) {
        $(preview).off('scroll', scrollEditorAccordingToPreview);
    } else {
        $(preview).on('scroll', scrollEditorAccordingToPreview);
    }
    scrollSyncEnabled = ! scrollSyncEnabled;
}

function openFullscreen() {
    $('html, body').addClass('body-fs');
    resizeEditor();
}

function resizeEditor() {
    var lineHeight = editor.renderer.lineHeight;
    var maxLines = document.getElementById('editor-wrapper').offsetHeight / lineHeight;
    editor.setOption('maxLines', Math.floor(maxLines));
    editor.resize();
};

function enableDisableSaveButton() {
    $('#btn-save-wrapper').tooltip('destroy');
    if (! liveTutorialEnabled) {
        var title = $('input[name=title]').val();
        /* Stack can be empty as a catch-all for a guide that doesn't fit into
         * any existing category.  However, title is essential. */
        if (!title) {
            $('#btn-save').prop('disabled', true);
            $('#btn-save-wrapper').tooltip({title: 'This article requires a title to be saved.'});
        } else {
            $('#btn-save').prop('disabled', false);
        }
    }
}

/* This requires Twitter bootstraps Modal.js! */
var addModalMessage = function(message) {
    $('#modal-content').html('<p>' + message + '</p>');
    $('#modal-error').modal()
};

function save(sha, path, secondary_repo, first_commit) {
    var data = {
        'title': $('input[name=title]').val(),
        'original_stack': $('input[name=original_stack]').val(),
        'stacks': $('#stacks').val(),
        'content': editor.getSession().getValue(),
        'sha': sha,
        'path': path,
        'first_commit': first_commit
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
            $('#editor-options').prop('disabled', true);
            $('#btn-back').prop('disabled', true);
            $('#btn-save').prop('disabled', true);
            return true;
        },
        complete: function(xhr, txt_status) {
        },
        success: function(data) {
            console.log(data);
            console.log(data.msg);
            clearLocalSave(current_local_filename);
            window.location.href = data.redirect;
        },
        error: function(response) {
            $('html, body').css("cursor", "auto");
            $('#editor-options').prop('disabled', true);
            $('#btn-back').prop('disabled', false);
            $('#btn-save').prop('disabled', false);
            var status = response.status;
            var data = response.responseJSON;
            console.log(status, data);
            if (data && data.error) {
                addModalMessage(data.error);
            }
            if (data && data.redirect) {
                setTimeout(function(){ window.location.href = data.redirect; }, 1000);
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

    /* From utils.js */
    if (supports_html5_storage()) {
        localStorage['hack.guides-show-help'] = isHelpEnabled;
    }
}

function hideHelp() {
    $('#editor-help').fadeOut('fast');
    $('#editor-help').hide();
    isHelpEnabled = false;

    /* From utils.js */
    if (supports_html5_storage()) {
        localStorage['hack.guides-show-help'] = isHelpEnabled;
    }
}


/* Show each section 1 at a time in help. This only works for full-screen mode
 * because these buttons are visible otherwise. */
function init_editor_help() {
    help_sections = $('#editor-help').find('.section');

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

    /* From utils.js */
    if (supports_html5_storage()) {
        if (localStorage['hack.guides-show-help'] == 'false') {
            hideHelp();
            return;
        }
    }

    showHelp();
    goto_section(0);
}
