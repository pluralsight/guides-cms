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

    for guide in xml_for_guides(guides):
        items.append(guide)

    items.append('</urlset>')

    return '\n'.join(items)


def xml_for_guides(guides):
    """
    Iterator through XML strings for each guide

    :param guides: List of file_mod.file_listing_item items
    """

    for guide in guides:
        yield '<url><loc>%s</loc><changefreq>daily</changefreq></url>' % (
               guide.url)
