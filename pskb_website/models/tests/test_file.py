"""
Tests for models.file module
"""

from .. import file as file_mod


def test_parsing_title_line():
    # Make sure we can handle 'by' being in the title
    line = '### This is how article title by A Coder with a long name'
    title, name = file_mod._parse_title_line(line)

    assert title == 'This is how article title'
    assert name == 'A Coder with a long name'

    line = '### This is how to parse code by using Python by A Programmer'
    title, name = file_mod._parse_title_line(line)

    assert title == 'This is how to parse code by using Python'
    assert name == 'A Programmer'


def test_parsing_url_line():
    line = '[Read the awesome guide](http://tutorials.pluralsight.com/review/a-beginners-guide-to-jquery)'

    text, url = file_mod._parse_url_line(line)

    assert text == 'Read the awesome guide'
    assert url == 'http://tutorials.pluralsight.com/review/a-beginners-guide-to-jquery'


def test_parse_author_info_line():
    line = '[Read more guides from Carl Smith](http://tutorials.pluralsight.com/user/carlsmith) <img src="https://avatars.githubusercontent.com/u/7561668?v=3" />'

    name, img_url = file_mod._parse_author_info_line(line)

    assert name == 'carlsmith'
    assert img_url == 'https://avatars.githubusercontent.com/u/7561668?v=3'


def test_parse_stacks_line():
    line = 'Related to: Front-End JavaScript (Angular, React, Meteor, etc), Python, C/C++'

    # Everything is returned lower case to normalize things for callers
    stacks = ['front-end javascript (angular, react, meteor, etc)', 'python',
              'c/c++']
    assert file_mod._parse_stacks_line(line) == stacks


def test_iter_article_sections_from_file_listing():
    text = """
### A Beginners Guide to jQuery by Carl Smith
- [Read the guide](http://tutorials.pluralsight.com/review/a-beginners-guide-to-jquery)
- [Read more from Carl Smith](http://tutorials.pluralsight.com/user/carlsmith) <img src="https://avatars.githubusercontent.com/u/7561668?v=3" /> 
- Related to: Front-End JavaScript (Angular, React, Meteor, etc)

### JavaScript Callbacks Variable Scope Problem by Itay Grudev
- [Read the guide](http://tutorials.pluralsight.com/review/javascript-callbacks-variable-scope-problem)
- [Read more from Itay Grudev](http://tutorials.pluralsight.com/user/itay-grudev)
- Related to: Front-End JavaScript (Angular, React, Meteor, etc)
- [Thumbnail](https://raw.githubusercontent.com/durden/articles/master/images/dc622a2f-673c-4466-ade3-3b1122dc7d6d.jpg)
"""

    lines = list(file_mod._iter_article_sections_from_file_listing(text))

    assert len(lines) == 2

    section_1 = [
        '### A Beginners Guide to jQuery by Carl Smith',
        '- [Read the guide](http://tutorials.pluralsight.com/review/a-beginners-guide-to-jquery)',
        '- [Read more from Carl Smith](http://tutorials.pluralsight.com/user/carlsmith) <img src="https://avatars.githubusercontent.com/u/7561668?v=3" />',
        '- Related to: Front-End JavaScript (Angular, React, Meteor, etc)']

    assert lines[0] == section_1

    section_2 = [
        '### JavaScript Callbacks Variable Scope Problem by Itay Grudev',
        '- [Read the guide](http://tutorials.pluralsight.com/review/javascript-callbacks-variable-scope-problem)',
        '- [Read more from Itay Grudev](http://tutorials.pluralsight.com/user/itay-grudev)',
        '- Related to: Front-End JavaScript (Angular, React, Meteor, etc)',
        '- [Thumbnail](https://raw.githubusercontent.com/durden/articles/master/images/dc622a2f-673c-4466-ade3-3b1122dc7d6d.jpg)']

    assert lines[1] == section_2


def test_parsing_listing_text():
    text = """
### A Beginners Guide to jQuery by Carl Smith
- [Read the guide](http://tutorials.pluralsight.com/review/a-beginners-guide-to-jquery)
- [Read more from Carl Smith](http://tutorials.pluralsight.com/user/carlsmith) <img src="https://avatars.githubusercontent.com/u/7561668?v=3" />
- Related to: Front-End JavaScript (Angular, React, Meteor, etc)

### JavaScript Callbacks Variable Scope Problem by Itay Grudev
- [Read the guide](http://tutorials.pluralsight.com/review/javascript-callbacks-variable-scope-problem)
- [Read more from Itay Grudev](http://tutorials.pluralsight.com/user/itay-grudev)
- Related to: Front-End JavaScript (Angular, React, Meteor, etc)
- [Thumbnail](https://raw.githubusercontent.com/durden/articles/master/images/dc622a2f-673c-4466-ade3-3b1122dc7d6d.jpg)
"""

    test_articles = list(file_mod.read_items_from_file_listing(text))
    correct_articles = [
        file_mod.file_listing_item(
            'A Beginners Guide to jQuery',
            'http://tutorials.pluralsight.com/review/a-beginners-guide-to-jquery',
            'carlsmith',
            'Carl Smith',
            'https://avatars.githubusercontent.com/u/7561668?v=3',
            None,
            ['front-end javascript (angular, react, meteor, etc)']),

        file_mod.file_listing_item(
            'JavaScript Callbacks Variable Scope Problem',
            'http://tutorials.pluralsight.com/review/javascript-callbacks-variable-scope-problem',
            'itay-grudev',
            'Itay Grudev',
            None,
            'https://raw.githubusercontent.com/durden/articles/master/images/dc622a2f-673c-4466-ade3-3b1122dc7d6d.jpg',
            ['front-end javascript (angular, react, meteor, etc)']),
    ]

    assert test_articles == correct_articles


def test_parsing_listing_text_without_stacks():
    text = """
### A Beginners Guide to jQuery by Carl Smith
- [Read the guide](http://tutorials.pluralsight.com/review/a-beginners-guide-to-jquery)
- [Read more from Carl Smith](http://tutorials.pluralsight.com/user/carlsmith) <img src="https://avatars.githubusercontent.com/u/7561668?v=3" />
- Related to: Front-End JavaScript (Angular, React, Meteor, etc)

### JavaScript Callbacks Variable Scope Problem by Itay Grudev
- [Read the guide](http://tutorials.pluralsight.com/review/javascript-callbacks-variable-scope-problem)
- [Read more from Itay Grudev](http://tutorials.pluralsight.com/user/itay-grudev)
- [Thumbnail](https://raw.githubusercontent.com/durden/articles/master/images/dc622a2f-673c-4466-ade3-3b1122dc7d6d.jpg)
"""

    test_articles = list(file_mod.read_items_from_file_listing(text))
    correct_articles = [
        file_mod.file_listing_item(
            'A Beginners Guide to jQuery',
            'http://tutorials.pluralsight.com/review/a-beginners-guide-to-jquery',
            'carlsmith',
            'Carl Smith',
            'https://avatars.githubusercontent.com/u/7561668?v=3',
            None,
            ['front-end javascript (angular, react, meteor, etc)']),

        file_mod.file_listing_item(
            'JavaScript Callbacks Variable Scope Problem',
            'http://tutorials.pluralsight.com/review/javascript-callbacks-variable-scope-problem',
            'itay-grudev',
            'Itay Grudev',
            None,
            'https://raw.githubusercontent.com/durden/articles/master/images/dc622a2f-673c-4466-ade3-3b1122dc7d6d.jpg',
            []),
    ]

    assert test_articles == correct_articles


def test_get_updated_file_listing_text():
    start_text = """
### A Beginners Guide to jQuery by Carl Smith
- [Read the guide](http://tutorials.pluralsight.com/review/a-beginners-guide-to-jquery)
- [Read more from Carl Smith](http://tutorials.pluralsight.com/user/carlsmith) <img src="https://avatars.githubusercontent.com/u/7561668?v=3" />
- Related to: Front-End JavaScript (Angular, React, Meteor, etc)

### JavaScript Callbacks Variable Scope Problem by Itay Grudev
- [Read the guide](http://tutorials.pluralsight.com/review/javascript-callbacks-variable-scope-problem)
- [Read more from Itay Grudev](http://tutorials.pluralsight.com/user/itay-grudev)
- [Thumbnail](https://raw.githubusercontent.com/durden/articles/master/images/dc622a2f-673c-4466-ade3-3b1122dc7d6d.jpg)""".lstrip()

    item = file_mod.file_listing_item(
            'New article',
            'http://localhost.com/new-article',
            'me',
            'Test name',
            'http://localhost.com/user/me.jpg',
            'http://localhost.com/user/thumbnail.jpg',
            ['Python', 'Front-End JavaScript (Angular, React, Meteor, etc)'])

    author_url = 'http://localhost.com/user/%s' % (item.author_name)

    new_article = """
### {title} by {author_name}
- [Read the guide]({url})
- [Read more from {author_name}]({author_url}) <img src="{author_img}" width="30" height="30" alt="{author_name}" />
- Related to: {stacks}
- [Thumbnail]({thumbnail})""".format(title=item.title,
                                     author_name=item.author_name,
                                     url=item.url,
                                     author_url=author_url,
                                     author_img=item.author_img_url,
                                     thumbnail=item.thumbnail_url,
                                     stacks=','.join(item.stacks)).lstrip()

    correct_text = "%s\n\n%s" % (new_article, start_text)

    new_text = file_mod.get_updated_file_listing_text(start_text,
                                                      item.url,
                                                      item.title,
                                                      author_url,
                                                      item.author_name,
                                                      item.author_img_url,
                                                      item.thumbnail_url,
                                                      item.stacks)

    assert new_text == correct_text


def test_get_updated_file_listing_text_with_empty_start():
    text = ''

    item = file_mod.file_listing_item(
            'New article',
            'http://localhost.com/new-article',
            'me',
            'Test name',
            'http://localhost.com/user/me.jpg',
            'http://localhost.com/user/thumbnail.jpg',
            ['Python', 'Front-End JavaScript (Angular, React, Meteor, etc)'])

    author_url = 'http://localhost.com/user/%s' % (item.author_name)

    new_text = file_mod.get_updated_file_listing_text(text,
                                                      item.url,
                                                      item.title,
                                                      author_url,
                                                      item.author_name,
                                                      item.author_img_url,
                                                      item.thumbnail_url,
                                                      item.stacks)

    correct_text = """
### {title} by {author_name}
- [Read the guide]({url})
- [Read more from {author_name}]({author_url}) <img src="{author_img}" width="30" height="30" alt="{author_name}" />
- Related to: {stacks}
- [Thumbnail]({thumbnail})""".format(title=item.title,
                                     author_name=item.author_name,
                                     url=item.url,
                                     author_url=author_url,
                                     author_img=item.author_img_url,
                                     thumbnail=item.thumbnail_url,
                                     stacks=','.join(item.stacks)).lstrip()

    assert new_text == correct_text


def test_get_updated_file_listing_text_changed_article():
    start_text = """
### A Beginners Guide to jQuery by Carl Smith
- [Read the guide](http://tutorials.pluralsight.com/review/a-beginners-guide-to-jquery)
- [Read more from Carl Smith](http://tutorials.pluralsight.com/user/carlsmith) <img src="https://avatars.githubusercontent.com/u/7561668?v=3" />
- Related to: Front-End JavaScript (Angular, React, Meteor, etc)

### JavaScript Callbacks Variable Scope Problem by Itay Grudev
- [Read the guide](http://tutorials.pluralsight.com/review/javascript-callbacks-variable-scope-problem)
- [Read more from Itay Grudev](http://tutorials.pluralsight.com/user/itay-grudev)
- [Thumbnail](https://raw.githubusercontent.com/durden/articles/master/images/dc622a2f-673c-4466-ade3-3b1122dc7d6d.jpg)""".lstrip()

    article_lines = start_text.splitlines()[5:]

    # Use internal parsing functions for extra testing
    item = file_mod._parse_file_listing_lines(article_lines)

    # Add stacks and remove thumbnail
    item = file_mod.file_listing_item(
            item.title,
            item.url,
            item.author_name,
            item.author_real_name,
            item.author_img_url,
            None,
            ['Python', 'Front-End JavaScript (Angular, React, Meteor, etc)'])

    correct_text = """
### A Beginners Guide to jQuery by Carl Smith
- [Read the guide](http://tutorials.pluralsight.com/review/a-beginners-guide-to-jquery)
- [Read more from Carl Smith](http://tutorials.pluralsight.com/user/carlsmith) <img src="https://avatars.githubusercontent.com/u/7561668?v=3" />
- Related to: Front-End JavaScript (Angular, React, Meteor, etc)

### JavaScript Callbacks Variable Scope Problem by Itay Grudev
- [Read the guide](http://tutorials.pluralsight.com/review/javascript-callbacks-variable-scope-problem)
- [Read more from Itay Grudev](http://tutorials.pluralsight.com/user/itay-grudev)
- Related to: Python,Front-End JavaScript (Angular, React, Meteor, etc)""".lstrip()

    author_url = 'http://tutorials.pluralsight.com/user/itay-grudev'
    new_text = file_mod.get_updated_file_listing_text(start_text,
                                                      item.url,
                                                      item.title,
                                                      author_url,
                                                      item.author_real_name,
                                                      item.author_img_url,
                                                      item.thumbnail_url,
                                                      item.stacks)

    assert new_text == correct_text


def test_get_removed_file_listing_text():
    text = """
### A Beginners Guide to jQuery by Carl Smith
- [Read the guide](http://tutorials.pluralsight.com/review/a-beginners-guide-to-jquery)
- [Read more from Carl Smith](http://tutorials.pluralsight.com/user/carlsmith) <img src="https://avatars.githubusercontent.com/u/7561668?v=3" />
- Related to: Front-End JavaScript (Angular, React, Meteor, etc)

### JavaScript Callbacks Variable Scope Problem by Itay Grudev
- [Read the guide](http://tutorials.pluralsight.com/review/javascript-callbacks-variable-scope-problem)
- [Read more from Itay Grudev](http://tutorials.pluralsight.com/user/itay-grudev)
- [Thumbnail](https://raw.githubusercontent.com/durden/articles/master/images/dc622a2f-673c-4466-ade3-3b1122dc7d6d.jpg)

### Guide 3
- [Read the guide](http://tutorials.pluralsight.com/review/here)
- [Read more from Itay Grudev](http://tutorials.pluralsight.com/user/durden)
- [Thumbnail](https://raw.githubusercontent.com/durden/articles/master/images/dc622a2f-673c-4466-ade3-3b1122dc7d6d.jpg)""".lstrip()

    title = 'A Beginners Guide to jQuery'
    new_text = file_mod.get_removed_file_listing_text(text, title)

    correct_text = """
### JavaScript Callbacks Variable Scope Problem by Itay Grudev
- [Read the guide](http://tutorials.pluralsight.com/review/javascript-callbacks-variable-scope-problem)
- [Read more from Itay Grudev](http://tutorials.pluralsight.com/user/itay-grudev)
- [Thumbnail](https://raw.githubusercontent.com/durden/articles/master/images/dc622a2f-673c-4466-ade3-3b1122dc7d6d.jpg)

### Guide 3
- [Read the guide](http://tutorials.pluralsight.com/review/here)
- [Read more from Itay Grudev](http://tutorials.pluralsight.com/user/durden)
- [Thumbnail](https://raw.githubusercontent.com/durden/articles/master/images/dc622a2f-673c-4466-ade3-3b1122dc7d6d.jpg)""".lstrip()

    assert new_text == correct_text
