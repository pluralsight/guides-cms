=========
CHANGELOG
=========

--------------------
version .3 - 11/3/16
--------------------

Bug Fixes
---------

- Fix bug with not checking for article existence on editor page
- Fix link for featured article after redesign
- Fix bug with file listing getting updated with publish status before it changed


--------------------
version .2 - 11/3/16
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
version .1 - 23/2/16
--------------------

Initial open source release during `<http://hacksummit.org>`_.
