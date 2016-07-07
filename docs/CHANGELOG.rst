=========
CHANGELOG
=========

--------------------
version .6 - 7/7/16
--------------------

New Features
------------

- Revamped design to be more colorful with stack images for every guide, etc. 
- `Added ability to heart guides <https://github.com/pluralsight/guides-cms/commit/c2cb70be200bcac851f24bd5e0390e5d70fda1d5>`_
    - Requires use of redis and use of `ENABLE_HEARTING` and `REDIS_HEARTS_DB_URL` environment variables
- `Support for Github Bio on profile and article pages <https://github.com/pluralsight/guides-cms/pull/104>`_
- `Improved support for Facebook Open Graph tags on homepage and article <https://github.com/pluralsight/guides-cms/pull/95>`_
- `Improved layout of review page and home page when there is no featured guide
  <https://github.com/pluralsight/guides-cms/commit/65fff27f34a3cb787298e65cb1ecd2ee604da3f9>`_
- `New stack images <https://github.com/pluralsight/guides-cms/pull/89>`_
    - Thanks `@eh3rrera <https://github.com/eh3rrera>`_!
- `Use Github webhooks to keep list of branches and cache up to date <https://github.com/pluralsight/guides-cms/pull/79>`_
    - Requires use of `WEBHOOK_SECRET` environment variable
- New page highlighting tutorial contest
- `Properly escape all code on article pages, not just HTML <https://github.com/pluralsight/guides-cms/pull/85/commits>`_

Bug Fixes
---------

- `Fix exception when running with empty REDISCLOUD_URL env variable <https://github.com/pluralsight/guides-cms/commit/10f9cf081c6652e29c37c1b5e326794fe21b7c8c>`_
- `Fix html escaping issues on article page <https://github.com/pluralsight/guides-cms/pull/103>`_
- `Shorten long author names to prevent from breaking out of design boxes <https://github.com/pluralsight/guides-cms/commit/535da3548cabe0d87d66af034a718c20af669dc2>`_
- `KeyError exception on some invalid page URLs <https://github.com/pluralsight/guides-cms/commit/d32b677652e0c6306daad2914b11ed853019863f>`_
- `Ignore invalid statuses when reading article <https://github.com/pluralsight/guides-cms/commit/0a86098d63e9fedc7d61282b2b3b195b3fcaf10d>`_
- `Error when handling failed github authentication request <https://github.com/pluralsight/guides-cms/commit/066518c8fabe10d038af7fa166293d4c56018301>`_
- `Bug with removing a branch when it being added again <https://github.com/pluralsight/guides-cms/commit/7aa34565d775519d2315e67e6ccdd70b0d889c72>`_
- `Problem unpredictable featured guide when two guides have the same title <https://github.com/pluralsight/guides-cms/commit/e6beae19d78a767a8cde384da61337c28ed70ff8>`_

Changes
-------

- `Add CTA to article list when filtering returns no results <https://github.com/pluralsight/guides-cms/commit/6ec72ce056b4d063e3251a16343ddc5eb0de03a1>`_
- `Guides are now grouped by publish status on profile page <https://github.com/pluralsight/guides-cms/pull/105/commits/64210b755ce1a367cfc911be4f055dac99c58964>`_
- `All markdown is rendered on front-end with Javascript instead of using
  Github API <https://github.com/pluralsight/guides-cms/pull/86>`_
- `Changed copy on login page to be more informative <https://github.com/pluralsight/guides-cms/commit/1cd4f69d0a3d42d75888062b20dd6b88d3de2278>`_
- `New logo highlighting our sponsor, Pluralsight <https://github.com/pluralsight/guides-cms/pull/87>`_
- `Store featured guide with redis <https://github.com/pluralsight/guides-cms/commit/e6beae19d78a767a8cde384da61337c28ed70ff8>`_
- `Remove case-insensitive comparison for featured guide environment variable
  <https://github.com/pluralsight/guides-cms/commit/ce8f0a053729fc6103263a928cbc7c57e93b76c1>`_

--------------------
version .5 - 5/9/16
--------------------

New Features
------------

- Logging of Github API rate limit
    - See `bin/rate_limit_watcher.py` which can be used with Heroku Scheduler
      add-on or `cron` in any UNIX environment
- Added `newrelic` to requirements for performance monitoring
    - This is optional, but still in the `requirements.txt` file.
- Added full-screen editor as default and removed non-full screen
    - This resulted in a lot of improvments including simpler CSS, better
      integrated help, tooltips, modal error dialogs, and a full-screen view
      with all possible controls readily available.
- `Big speed improvements to editor <https://github.com/pluralsight/guides-cms/pull/47>`_
- `Added links to hack.pledge and hack.summit in header <https://github.com/pluralsight/guides-cms/pull/42>`_
- `Show list of contributors on guide page <https://github.com/pluralsight/guides-cms/pull/45>`_

Bug Fixes
---------

- `Edit guide link is broken after changing publish status <https://github.com/pluralsight/guides-cms/issues/70>`_
- `Editor removes escape characters even if in a codeblock <https://github.com/pluralsight/guides-cms/issues/64>`_
- `Prevent extra commit to metadata file on first edit <https://github.com/pluralsight/guides-cms/issues/67>`_
- `Image uploader doesn't set committer name correctly on commits <https://github.com/pluralsight/guides-cms/issues/66>`_
- `Fixed URLs involving a branch name with special characters <https://github.com/pluralsight/guides-cms/commit/ea3ed3bc16485277fe767bf14f2490f27cfadb3f>`_
- `Fixed problems with guide titles having special URL characters <https://github.com/pluralsight/guides-cms/commit/d91c3555352f5fbf72ad44587496f8dc1f933f92>`_
- `Remove unecessary Github API request when fetching contributor lists <https://github.com/pluralsight/guides-cms/commit/e345ee1638ffb753ef9f132484ea9101a97be0db>`_
- `Fetching contributors lists twice for guides with no contributors <https://github.com/pluralsight/guides-cms/commit/e848a8731335ba9ebc9c84c4937fc39b3f0dc4ea>`_
- `Prevent mobile share buttons and email signup box overlapping <https://github.com/pluralsight/guides-cms/commit/7a065c646c536b7d5f5381fcd373552cdcb29dfb>`_
- `Incorrectly including any user with a branch as a contributor <https://github.com/pluralsight/guides-cms/commit/fbf5bc5a8516630317b817cc76f6b9863a987e40>`_
- `Faster loading of rendered markdown from Github API <https://github.com/pluralsight/guides-cms/commit/8793949e03dbf161c384c34e170aeaac2f2c5c24>`_
- `Fixed escape <script> tag in article content <https://github.com/pluralsight/guides-cms/pull/36>`_
- `Properly serialize file listing to cache with unicode <https://github.com/pluralsight/guides-cms/commit/4b58aa08aa94fd5a2668220c994a1ff954ab5912>`_
- `Properly show featured guide on my-drafts page <https://github.com/pluralsight/guides-cms/commit/d41fc34d1e71160d866d25a96dcd9091b69e03b6>`_
- `Add contributor page with leaderboards <https://github.com/pluralsight/guides-cms/commit/10bd2c6cc88a0149597ed68c785e0fbc376dfb34>`_
    - Introduces `IGNORE_STATS_FOR` environment variable

Changes
-------

- `Disable save button on editor until a title has been chosen <https://github.com/pluralsight/guides-cms/pull/69>`_
- `Improved 'Live Markdown Tutorial' UI to include a more prominent 'Close
  Tutorial' button <https://github.com/pluralsight/guides-cms/pull/69>`_
- `Renamed 'Cancel' button on editor to 'Back' <https://github.com/pluralsight/guides-cms/pull/69>`_
- `Branches are named after user and guide, not just user <https://github.com/pluralsight/guides-cms/issues/58>`_
    - Makes merging changes much easier since each branch only deals with a
      single guide
- `Improved load time of FAQ page <https://github.com/pluralsight/guides-cms/issues/59>`_
- `Redirect to master branch if branched guide is missing <https://github.com/pluralsight/guides-cms/issues/50>`_
- `Do not show users in IGNORE_STATS_FOR environment variable in contributor
  lists <https://github.com/pluralsight/guides-cms/commit/e345ee1638ffb753ef9f132484ea9101a97be0db>`_
- `Use username/login in profile page title <https://github.com/pluralsight/guides-cms/commit/cffd8b0ebe039c367ada696b8b3e951cdf4b1867>`_
- 'Allow redirect URLs file to contain markdown lists `<https://github.com/pluralsight/guides-cms/commit/a83155605492dd7da65af662de1e3d937f56be68>`_

--------------------
version .4 - 4/5/16
--------------------

New Features
------------

- Live markdown tutorial in new editor
- Auto save guide text using HTML5 local storage
- Side-by-side markdown preview
- Optional scroll-sync between text and markdown preview panes
- Ability to add images to guides via standard file dialog
- Support for 301 redirects for guides (see :ref:`redirects file <redirects_file>`)
- Easier signup to Slack community via popup box on FAQ page

Bug Fixes
---------

- Links in editor preview open in new tabs
- Use proper HTTP status codes for redirects requiring authentication
- Properly escape characters in Table of Contents (see `issue <https://github.com/pluralsight/guides-cms/issues/29>`_
- Incorrect links to branched guides on main guide page
- Overlapping of table of contents with footer
- Do not show users' drafts on profile page unless logged in as user
- Prevent errors on redundant publish status changes
- Prevent making API calls for URLs that do not look like guides on guide page
- Issue losing list of branches when saving original article after branched
- Issue with /user/ returning articles of repo owner instead of error
- Making a commit with wrong user name by incorrectly reading user cache (see `commit <https://github.com/pluralsight/guides-cms/commit/495efee1149cc8d8731b218ef2a81c5787aa77b3>`_
- Maintain social share counts for po.st with new URL structure introduced in v.3

Changes
-------

- Changed editor from `Bootstrap Markdown editor <http://www.codingdrama.com/bootstrap-markdown/>`_ to `Ace <https://ace.c9.io/>`_
- Show published guides instead of error page when unable to find requested guide
- Improved caching of file listings for homepage and review pages
- Add better explanation of publish workflow after submitting a new guide
- Improve error message when creating duplicate guide with title/stack
- Removed redundant 'Edit guide' link in header on guide page
- Removed form to set featured article
- Use /author/<name>/ URL for authors instead of user, 301 redirect from /user/<name>

--------------------
version .3 - 3/11/16
--------------------

Bug Fixes
---------

- Fix bug with not checking for article existence on editor page
- Fix link for featured article after redesign
- Fix bug with file listing getting updated with publish status before it changed


--------------------
version .2 - 3/11/16
--------------------

Changes
-------

1. Three stage publish workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Draft**

The initial stage where all guides start out in.  Guides in this stage are not
visible by anyone other than the original author. [1]

**All guides marked as unpublished will be moved to draft stage during the
upgrade process.**  Therefore, initially there will be no guides in the
in-review stage.

**In-review**

The second stage were guides go that are ready for community editing help.  Any
user can mark their guide as 'in-review' from dropdown at the bottom of the
guide page.

Guides should only be marked as 'in-review' when they are complete and ready
editing help.

**Please don't mark partially completed guides as in-review.** This will
necessarily waste community editors time reviewing guides that are not
completed.

Guides marked as 'in-review' will show up on the 'Review' page.

**Published**

The final stage for fully edited articles is published.  This is the stage
where the community editors have decided a guide is ready for the world to see.
Only community editors can move a guide into the published stage.

Published articles will be available on the homepage of the site.

2. Redesign of the content repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The content repository is currently a flat structure.  This means all the
guides are directly at the top level of the repository, which makes it
difficult to easily navigate on the github.com repository view.  This pull
request reorganizes the repository to use a more intuitive and nested layout
based on the publish status of the guide as well as the stack.  For example,
each publish stage will have a folder with a nested folder for each stack:

This will make quickly browsing the content much easier on github.com.

3. URL redesign (with backwards compatability)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The URL scheme has been redesigned to include the stack.  This gives visitors
more insight into the type of guide by looking only at the URL.

Therefore, the guide URL will now be something like:

- `/python/my-awesome-guide`

instead of

- `/my-awesome-guide`

All the old URLs with only the title remain intact with a 301 redirect at the
`/review/` endpoint.

Also, the status of a guide is represented by a query string, not directly in
the URL as before.  So, the following URL will point to a guide in the
in-review stage:

- `/python/my-awesome-guide?status=in-review`

instead of

- `/review/my-awesome-guide`

This will allow articles to keep the same URL through the entire publish
workflow, improving their SEO and link maintainability.  In addition, visitors
can clearly see in the URL the publish status of a guide.  Soon there will be a
more visual way to see the status on the guide page itself, but not in this
change.

Note that changing the stack of your article **will** change the URL of your
guide.  Therefore, change this with caution to avoid losing any SEO you might
have gathered on the old URL.  Typically you should not be changing your stack
after you're in the 'in-review' stage.

4. Github commits only involve guide author
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Previously all commits to guides were pushed to github with a different author
and committer.  The committer was marked as the owner of the content
repository.  This lead to a commit having a different author and committer,
which is confusing on github.com.  Now all commits will have the same committer
and author to avoid this confusion.  **You as the author still get full
contribution credit, which will show up on your github.com profile.** This
change just gives you commit credit **by youreself.**

5. Ability to change stack guide
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is not a recommended action because it will change a guides URL, which is
not ideal for SEO and link preservation.  However, it is now allowed.

Upgrading
^^^^^^^^^

See the upgrade_repo_layout_fromv.1.py script for details on the content
repository conversion process.  The upgrade script will use `git mv` to move
all guide diretories to their new locations thereby retaining the commit
history.

**All guides marked as unpublished will be moved to draft stage during the
upgrade process.**  Therefore, initially there will be no guides in the
in-review stage.

1. Run upgrade script on your content repository
2. Run merge_branches.py and use the branch you used from step 1 to merge with.
3. Push all remote branches to origin
4. Push your master branch to origin
5. Deploy new version of the CMS
6. Run `disqus redirect crawler <https://help.disqus.com/customer/en/portal/articles/912834-redirect-crawler>`_ to update URLs for all comments.

[1] We don't have strict privacy since the guides are also available on
github.com.  So, technically a draft guide can still be viewed directly on
github, but there will be no way for users to see draft guides directly on the
content website.

Bug Fixes
---------

- Improve commit messages when removing guides

--------------------
version .1 - 2/23/16
--------------------

Initial open source release during `<http://hacksummit.org>`_.
