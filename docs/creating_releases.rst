===============
Release Process
===============

The following document explains the manual release process.

1. Prepare release notes
    - Run `git tag` to see release names
    - Run `git log <prev_tag>..HEAD` to see all changes since last release.
    - We typically only pick out the large changes that will affect users or
      developers.
2. Add notes to `CHANGELOG` file in restructed text format
3. Pick a release name
    - We're loosely using semantic versioning.
4. Create a tag locally for the release name
    - `git tag <name>`
5. Push tag to github.com
    - `git push origin <name>`
6. Add release notes to github.com
    - Click 'releases' tab on main github project page
    - Click 'tags'
    - Click 'Add release notes'
    - Fill out info in markdown!

    ** Yes, it's annoying we have release notes in rst and markdown.** We could
    potentially automate this or remove the redundancy in the future. Pull
    Requests for this would be accepted. :)
