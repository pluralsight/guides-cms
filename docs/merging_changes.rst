=====================
Merging guide changes
=====================

Hopefully you'll be getting lots of suggestions from readers on how to improve the guides or fix bugs in the code.  This page describes the process of merging those changes into your `master` branch so everyone can see the results of this collaborative process.

Currently merging changes to guides' is a manual process handled via the github.com website or locally with `git`.  This is because merging suggestions needs to be verified by an editor and/or the original guide author.  Here's the normal process after a user has suggested a change via the CMS website:

-----------------------------
Simple merges with github.com
-----------------------------

1. Create a pull request on github.com for the branch
    - Browse the branches of the content repository and click the 'New pull request' button associated with the branch you want to integrate.
2. Review the changes in the pull request on github.com
3. You can automatically merge the changes via github.com if the changes merge cleanly and you want **all** of the changes.
4. Edit the `details.json` file for the guide you just merged changes into and remove the branch you just integrated.
    - This can also be done via github.com by browsing to the `details.json` file and using the 'edit' button.
5. Delete the branch you just merged on github.com
    - Browse the branches again and click the trash can icon next to the branch

---------------------------------
Complex merges aka the hacker way
---------------------------------

Often times you'll only want part of the changes, or you want to handle any conflicts.  This is a more involved process, which we recommend using the command-line Git interface.  You can also use any Git GUI you prefer, but we're describing the command-line approach since it's the most universal.

Integrating all changes from branch
-----------------------------------

1. Clone the content repository locally
    - Use `git clone <url>` where `<url>` is the URL for the repository from
      the main github repository page.
2. Make sure all the remote branches are up to date
    - Run `git fetch origin`
3. Checkout the remote branch you want to integrate
    - Run `git checkout -b <branch_name> origin/<branch_name>` where `<branch_name>` is the name of the branch you want to integrate.  This is typically the username of the github user who's suggesting the changes.
4. Merge the master branch to make sure the branch only introduces new changes
    - Run `git merge master`
    - Fix any conflicts and commit the merge
5. Switch back to the master branch and merge the branch
    - Run `git checkout master`
    - Run `git merge <branch_name>`
6. Edit the `details.json` file for the guide you just merged changes into and
   remove the branch you just integrated.
    - You can do this directly by editing the `details.json` file or using github.com by by browsing to the `details.json` file and using the 'edit' button.
    - **Be careful to remove any trailing commas from the branches list if you remove the last branch.  Remember, this file must be valid JSON syntax!**
7. Delete the branch you just merged on github.com
    - Run `git push origin :<branch_name>` to remove the branch from github.com.  You can also do this via github.com by browsing the branches again and clicking the trash can icon next to the branch.
8. Push the changes to github.com
    - Run `git push origin master`

Integrating some changes from branch
------------------------------------

1. Clone the content repository locally
    - Use `git clone <url>` where `<url>` is the URL for the repository from the main github repository page.
2. Look at the commit(s) you want to integrate a portion of
    - Run `git log -p <sha>` to see the changes.
    - You can use `git diff -b <sha>..<prev_sha>` to see the changes without any whitespace and/or line-ending changes.
3. Manually apply the changes you want to the master branch.
4. Commit the changes as the original user to make sure they get credit
    - Copy the 'Author:' line from the original commit you're integrating.  See output of `git log -p <sha>` from step 2.
    - Add the changes to staging with `git add <filename>`
    - Finally, commit the changes as the original author with `git commit --author=<author_info>` where `<author_info>` is the information for the original author.
5. Edit the `details.json` file for the guide you just merged changes into and
   remove the branch you just integrated.
    - You can do this directly by editing the `details.json` file or using github.com by by browsing to the `details.json` file and using the 'edit' button.
    - **Be careful to remove any trailing commas from the branches list if you remove the last branch.  Remember, this file must be valid JSON syntax!**
6. Delete the branch you just merged on github.com
    - Run `git push origin :<branch_name>` to remove the branch from github.com.  You can also do this via github.com by browsing the branches again and clicking the trash can icon next to the branch.
7. Push the changes to github.com
    - Run `git push origin master`

-----------------------------------
Easier visualizing of complex diffs
-----------------------------------

Often times prose is harder to diff than code because the length of a line can
be very long.  For example, it's common for an entire paragraph to be a single
line in prose whereas software is usually broken up into small lines with hard
linebreaks.

This means a diff for prose could show a large change when in reality on a few
words were changed.  The diff tools on github.com and `git` can help here if
you know the right options to use.

Github.com
----------

Github.com defaults to 'source diff view, but you can change this in the
top-right hand corner of any commit page.  Try clicking the 'rich diff' icon
next to the 'view' button for a different view.

Git
---

First, try using `git log --word-diff=color -p` to see diffs.  Another trick is
to find the two adjacent commits on a file and do something like the
`git diff --word-diff=color d98909743b32df2f44e835162f50e5b6b7f92c1c..8bc2725698b84d95014b0124c141a08b1946718 in-review/ruby-ruby-on-rails/handling-file-upload-using-ruby-on-rails-5-api/article.md`

You can get the two adjacent commits for a file by running `git log --follow
<path_to_file>`.
