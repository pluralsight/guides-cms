========
Contests
========

You can run contests that give authors an additional option to select a contest
category when writing a guide.  This shows up as a drop-down box under the
standard 'Stacks' drop-down on the editor page.

Authors can choose to enter the contest by selecting a contest category, if no
category is chosen the guide is not entered.  A guide that has entered a
contest will have 2 additional fields of metadata, a list of categories and the
contest name.

------------------
Starting a contest
------------------

1. Set the `CONTEST_NAME` environment variable to the unique name you want to
   identify a single contest.
2. Create a file called `contest_categories.md` at the root level of your
   content repository
3. File the `contest_categories.md` file with a list of categories for your
   contest. Put 1 category per line in the file

----------------
Ending a contest
----------------

1. Unset the `CONTEST_NAME` environment variable
