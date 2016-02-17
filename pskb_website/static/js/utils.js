"use strict";

/* Read headers from article as jquery object and put TOC in div_to_fill as
 * jquery object. */
function populate_table_of_contents(article, div_to_fill) {
    var headers = find_all_headers_without_ids(article);
    if (!headers.length) {
        div_to_fill.css("display", "none");
    } else {
        var new_toc = create_toc_from_headers(headers);
        $(new_toc).appendTo(div_to_fill);
    }
}

function filter() {
    var stacks = document.getElementById("stacks");
    var selected_stacks = [];

    for (var ii=0; ii < stacks.length; ii++) {
        if (stacks[ii].selected) {
            selected_stacks.push(stacks[ii].value);
        }
    }

    var items_to_show = []
    $('.article-teaser').each(function(article_idx) {
        if (should_show($(this), selected_stacks)) {
            items_to_show.push($(this));
        } else {
            $(this).hide('slow');
        }
    });

    /* Now sort items by their ORIGINAL ORDER which is specified by the
     * data-row-num.  This ensures that we don't ever reorder items, just
     * show/hide them in their original order. */
    items_to_show.sort(function (a, b) {
        return a.attr('data-row-id') - b.attr('data-row-id');
    });

    shuffle_items_in_grid(items_to_show);
}


/* Reorganize all shown items 3 to a row in order they originally appeared. */
function shuffle_items_in_grid(items_to_show) {
    var item_idx = 0;
    var item;
    var num_on_row;
    var max_per_row = 3;
    var offset_class = 'col-md-offset-1';

    $('.article-row').each(function(row_idx) {
        num_on_row = 0;

        while (num_on_row < max_per_row && item_idx < items_to_show.length) {
            item = items_to_show[item_idx];

            /* Only first item on the row must be indented so everything is
             * centered. */
            if (!num_on_row) {
                item.addClass(offset_class);
            } else {
                item.removeClass(offset_class);
            }

            item.appendTo($(this));
            item.show('slow');
            item_idx++;
            num_on_row++;
        }
    });
}

function should_show(article, selected_stacks) {
    /* Selecting nothing effectively means show everything */
    if (!selected_stacks.length) {
        return true;
    }

    /* User picked specific stacks and this article has no stacks so hide
        it. */
    if (!$(article).find('.stack').length) {
        return false;
    }

    var show = false;
    $(article).find('.stack').each(function(stack_idx) {
        for (var ii=0; ii < selected_stacks.length; ii++) {
            if (this.textContent == selected_stacks[ii]) {
                show = true;
                break;
            }
        }
    });

    return show;
}

/* Pass in a jquery div element and get list of jquery header elements back
 * that are inside the given div. */
function find_all_headers_without_ids(div) {
    var headers = [];
    $(div).find("h1, h2, h3, h4, h5, h6").each(function(header_idx) {
        if (typeof $(this).attr("id") === "undefined") {
            headers.push(this);
        }
    });
    return headers;
}

/* Pass in a list of jquery header elements and get string of HTML that
 * represents a table of contents from those header tags. */
function create_toc_from_headers(headers) {
    var toc_html = "<ul>";

    for (var ii=0; ii < headers.length; ii++) {
        var hdr = headers[ii];
        var url_content = hdr.textContent.replace(/ /g, "-").toLowerCase();
        var re = /h(\d)/i;
        var hdr_num = parseInt(re.exec(hdr.tagName)[1]);

        /* Array creats n - 1 so we add one to compensate */
        var indent = Array(hdr_num + 1).join("&nbsp;");
        var tag = "<li>" + indent + "<a href='#" + url_content + "'>" + hdr.textContent + "</a></li>";

        $(hdr).attr('id', url_content);
        toc_html += tag
    }

    toc_html += "</ul>";
    return toc_html;
}


/* Turn any table tags in div into responsive tables by adding
 * bootstrap-specific markup around table */
function create_responsive_tables(div) {
    var tables = $(div).find('table');
    tables.wrap('<div class="table-responsive">');
    tables.addClass('table');
}

/* Change all external links to open in a new tab/window */
function create_external_links(id) {
    var links = $('a').filter(function() {
        return this.hostname && this.hostname !== location.hostname;
    });

    links.append('&nbsp;<span class="glyphicon glyphicon-new-window" aria-hidden="true" style="font-size: 10px;"></span>');
    links.attr("target", "_blank");
}

/* Confirm user typed DELETE in form and submit request for article deletion
 * This function works with confirm_deletion.html form.
 */
function confirm_delete() {
    var confirm_box = document.getElementById("confirm-box");

    if (confirm_box.value != 'DELETE') {
        return;
    }

    var form = document.createElement("form");
    form.action = "/delete/";
    form.method = "POST";

    var path = document.getElementById('article-path');
    form.appendChild(path.cloneNode());

    var branch = document.getElementById('article-branch');
    form.appendChild(branch.cloneNode());
    form.submit();
}
