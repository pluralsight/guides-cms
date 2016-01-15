function filter() {
    var stacks = document.getElementById("stacks");

    var selected_stacks = [];
    for (ii=0; ii < stacks.length; ii++) {
        if (stacks[ii].selected) {
            selected_stacks.push(stacks[ii].value);
        }
    }

    console.log('Selected ' + selected_stacks);

    $('.article-teaser').each(function(article_idx) {
        if (should_show($(this), selected_stacks)) {
            $(this).show('slow');
        } else {
            $(this).hide('slow');
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
        for (ii=0; ii < selected_stacks.length; ii++) {
            if (this.textContent == selected_stacks[ii]) {
                show = true;
                break;
            }
        }
    });

    return show;
}
