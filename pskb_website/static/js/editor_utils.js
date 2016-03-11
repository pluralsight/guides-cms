var editor;
var author_name;
var author_real_name;

function initialize_editor(name, real_name) {
    author_name = name;
    author_real_name = real_name;

    var editor = $('#md-editor-ta');
    editor.markdown({
        autofocus: true,
        resize: 'vertical',
        height: 500,
        onPreview: add_article_header_data,
        footer: '<div id="md-footer">Upload files by dragging & dropping</div>',
        //or <a href="#" class="upload-img">selecting them</a></div>',
        dropZoneOptions: {
            url: '/img_upload/',
            disablePreview: true,
            maxFileSize: 3, // In Megabytes

            /* Disabled temporarily because unable to correctly get position of
             * cursor when clicking this. The image is always inserted at the
             * top of the text box, not the cursor position. */
            //clickable: '.upload-img' // This points to element whose click will trigger selection of files.
        }
    });
}

function add_article_header_data(editor) {
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

    return header + editor.parseContent();
}


function save(sha, path, secondary_repo) {
    var form = document.createElement("form");
    form.action = "/save/";
    form.method = "POST";

    var content = document.getElementById("md-editor-ta");
    form.appendChild(content);

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
