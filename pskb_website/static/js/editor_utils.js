var editor;
var author_name;
var author_real_name;

function initialize_editor(local_filename, name, real_name, img_upload_url) {
    author_name = name;
    author_real_name = real_name;

    editor = new EpicEditor({
        container: 'epiceditor',
        textarea: "content",
        buttons: false,
        basePath: '/static/css/vendor/editor/epic',
        theme: {
            base: '/base/hackguides.css',
            editor: '/editor/hackguides.css',
            preview: '/preview/github.css',
        },
        button: {
            preview: false,
            fullscreen: false,
            bar: "auto"
        },
        localStorageName: 'epiceditor',
        parser: marked,
        clientSideStorage: true,
        file: {
            name: local_filename,
            defaultContent: '',
            autoSave: 100,
            defaultContent: '# Untitled \n\nStart writing your tutorial!',
        },
        focusOnLoad: false,
        useNativeFullscreen: false,
        autogrow: false
        }).load(
    function () {
    });

    editor.on('update', function () {
        /* Inject header information as it would appear on a regular page since
         * this content is not directly in the editor box */
        var header = get_article_header_data();
        document.querySelector('#epiceditor-preview').innerHTML = header + this.exportFile(null, 'html');
        $('pre code').each(function(i, e) {hljs.highlightBlock(e)});
    }).emit('update');

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
        editor.getElement('editor').body.innerHTML += fileMarkdown;
        // Scroll editor to bottom
        var body = editor.getElement('editor').body;
        body.scrollTop = body.scrollHeight;
        // Scroll preview to bottom
        var preview = document.getElementById('epiceditor-preview');
        preview.scrollTop = preview.scrollHeight;
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

    var content = document.createElement("input");
    content.name = "content";
    content.value = editor.exportFile("", "json");
    form.appendChild(content.cloneNode());

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
