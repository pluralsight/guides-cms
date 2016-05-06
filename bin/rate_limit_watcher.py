#!/usr/bin/env python

import requests

URL = 'http://tutorials.pluralsight.com/gh_rate_limit'

def main():
    resp = requests.get(URL)
    if resp.status_code == 200:
        print resp.content
    else:
        print 'Failed checking rate limit, status_code: %d' % (resp.status_code)


if __name__ == '__main__':
    main()
