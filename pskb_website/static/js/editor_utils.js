var editor;
var author_name;
var author_real_name;

function initialize_editor(name, real_name) {
    editor = new EpicEditor({
        clientSideStorage: false,
        textarea: "content",
        basePath: '/static/css/vendor/editor/',
        autogrow: true,
        theme: {
            base: '/themes/base/epiceditor.css',
            preview: '/themes/preview/github.css',
            editor: '/themes/editor/epic-light.css'
        },
    }).load();

    author_name = name;
    author_real_name = real_name;

    iframe = editor.getElement('previewerIframe');

    /* Have to dynamically stuff in the correct css in the iframe for the
     * editor */
    css = document.createElement('link');
    css.href = "/static/css/vendor/github.css";
    css.rel = "stylesheet";
    css.type = "text/css";
    iframe.contentDocument.head.appendChild(css);

    css = document.createElement('link');
    css.href = "/static/css/vendor/bootstrap.min.css";
    css.rel = "stylesheet";
    css.type = "text/css";
    iframe.contentDocument.head.appendChild(css);

    css = document.createElement('link');
    css.href = "/static/css/base.css";
    css.rel = "stylesheet";
    css.type = "text/css";
    iframe.contentDocument.head.appendChild(css);

    /* Inject header information as it would appear on a regular page since
     * this content is not directly in the editor box */
    editor.on('preview', add_article_header_data);
}

function add_article_header_data() {
    var preview_div = editor.getElement('previewerIframe').contentDocument.getElementById('epiceditor-preview');
    var title = document.getElementById('title').value;

    var header = document.createElement('div');
    header.className = 'header';

    var h1 = document.createElement('h1')
    h1.id = 'title';
    h1.className = 'tagline gradient-text';
    h1.textContent = title;
    header.appendChild(h1);

    var h4 = document.createElement('h4');
    h4.id = 'author';

    var small = document.createElement('small');
    small.textContent = 'written by ';

    var anchor = document.createElement('a');

    if (author_real_name != undefined && author_real_name != '') {
        anchor.textContent = author_real_name;
    } else if (author_name != undefined && author_name != '') {
        anchor.textContent = author_name;
    } else {
        anchor.textContent = 'you';
    }

    if (author_name != undefined && author_name != '') {
        anchor.href = '/user/' + author_name;
    }

    small.appendChild(anchor);
    h4.appendChild(small);
    header.appendChild(h4);

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
        var h5 = document.createElement('h5');
        h5.id = 'related';
        var small = document.createElement('small');
        small.textContent = 'Related to ' + stacks;

        h5.appendChild(small);
        header.appendChild(h5);
    }

    header.appendChild(document.createElement('hr'));
    preview_div.insertBefore(header, preview_div.firstChild);
}


function save(sha, path, secondary_repo) {
    var form = document.createElement("form");
    form.action = "/save/";
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
