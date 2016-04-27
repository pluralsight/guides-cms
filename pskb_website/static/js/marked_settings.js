function decodeUTF8(s) {
    var i, d = unescape(encodeURIComponent(s)), b = new Uint8Array(d.length);
    for (i = 0; i < d.length; i++) b[i] = d.charCodeAt(i);
    return b;
}

function hash(text) {
    var hasher = new BLAKE2s(16);
    hasher.update(decodeUTF8(text));
    return hasher.hexDigest();
}


var renderer = new marked.Renderer();

renderer.getUniqueKey = function(text) {
    var key = hash(text);
    var index = 1;
    if (key in marked.hashDB) {
        index = marked.hashDB[key] + 1;
    }
    marked.hashDB[key] = index;
    return key + index;
}

renderer.heading = function (text, level) {
    var escapedText = text.toLowerCase().replace(/[^\w]+/g, '-');
    var key = this.getUniqueKey('heading' + level + escapedText);
    return '<h' + level + ' data-id="' + key + '" key="' + key + '"><a name="' + escapedText + '" class="anchor" href="#' + escapedText + '">' +
            '<span class="header-link"></span></a>' + text + '</h' + level + '>';
};

renderer.paragraph = function(text) {
    var key = this.getUniqueKey('paragraph' + text);
    return '<p data-id="' + key + '" key="' + key + '">' + text + '</p>';
};

renderer.list = function(body, ordered) {
    var type = ordered ? 'ol' : 'ul';
    var key = this.getUniqueKey(type + body);
    return '<' + type + ' data-id="' + key + '" key="' + key + '">' + body + '</' + type + '>';
};

renderer.blockquote = function(quote) {
    var key = this.getUniqueKey('blockquote' + quote);
    return '<blockquote data-id="' + key + '" key="' + key + '">' + quote + '</blockquote>';
};

renderer.table = function(header, body) {
    var key = this.getUniqueKey('table' + header + body);
    return '<table data-id="' + key + '" key="' + key + '">' + '<thead>'
        + header
        + '</thead>'
        + '<tbody>'
        + body
        + '</tbody></table>';
};

renderer.link = function(href, title, text) {
  if (this.options.sanitize) {
    try {
      var prot = decodeURIComponent(unescape(href))
        .replace(/[^\w:]/g, '')
        .toLowerCase();
    } catch (e) {
      return '';
    }
    if (prot.indexOf('javascript:') === 0 || prot.indexOf('vbscript:') === 0) {
      return '';
    }
  }
  var out = '<a href="' + href + '"';
  if (title) {
    out += ' title="' + title + '"';
  }
  out += ' target="_blank">' + text + '&nbsp;<span class="glyphicon glyphicon-new-window" aria-hidden="true" style="font-size: 10px;"></span></a>';
  return out;
};

renderer.code = function(code, lang, escaped) {
    var key = this.getUniqueKey('pre' + code + lang);
    escaped = true;
    if (lang == 'html') {
        code = _.escape(code)
    }
    if (!lang) {
        return '<pre data-id="' + key + '" key="' + key + '"><code>'
          + (escaped ? code : escape(code, true))
          + '\n</code></pre>';
    }

    return '<pre data-id="' + key + '" key="' + key + '"><code class="'
        + this.options.langPrefix
        + escape(lang, true)
        + '">'
        + (escaped ? code : escape(code, true))
        + '\n</code></pre>\n';
};

marked.setOptions({
    renderer: renderer,
    gfm: true,
    tables: true,
    breaks: true,
    pedantic: false,
    sanitize: false,
    smartLists: true,
    smartypants: false,
    // Slow performance because the virtual dom, lets highlight later
    // highlight: function (code) {
    //   return hljs.highlightAuto(code).value
    // }
});
marked.hashDB = {};

function markdown2html(md) {
    marked.hashDB = {};
    return marked(md);
}
