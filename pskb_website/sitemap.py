"""
Functionality to generate sitemap of guides
"""

import itertools

from .models import file as file_mod


def get_xml():
    """
    Get sitemap XML for published/in-review guides

    :return: String in XML format
    """

    items = ['<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    guides = itertools.chain(file_mod.published_articles(),
                             file_mod.in_review_articles())

    for guide in xml_for_guides(guides, depth=1):
        items.append(guide)

    items.append('</urlset>')

    return '\n'.join(items)


def xml_for_guides(guides, depth):
    """
    Iterator through XML strings for each guide

    :param guides: List of file_mod.file_listing_item items
    :param depth: Number of XML depth to apply to guides for 'pretty'
                  formatting
    """

    # Could use xml.etree and then pretty formatting, but xml is so simple just
    # easier to make it text
    url_depth = '\t' * depth
    loc_depth = '\t' * (depth + 1)

    for guide in guides:
        yield '%s<url>\n%s<loc>%s</loc>\n%s</url>' % (url_depth, loc_depth,
                                                      guide.url, url_depth)
