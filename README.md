[![Build][github-ci-image]][github-ci-link]
![License][license-image-mit]
# Label Bot

## Overview

This is a GitHub app for managing labels in a repository. It is written by and used in projects for
[@facelessuser](https://github.com/facelessuser). It uses the the persona of [@gir-bot](https://github.com/gir-bot), but
can technically use any user. Label Bot is not a publicly available service, but can be modified and installed in for
personal use in Heroku or some other hosting service.

Label bot handles a handful of label related scenarios:

- Label Bot can manage labels by syncing them up with a list specified in a configuration file. If the configuration
  file changes, labels will be added, edited, or removed (if enabled) to match the configuration.
- Label Bot can mark new issues and pull requests with specific labels. For instance, out of the box, it marks new
  issues with `triage`. New pull requests, and any new pushes to a pull request, are marked `needs-review`. This helps
  highlight issues that need attention.
- Label Bot will mark pull requests as pending if certain labels are present. By default it looks for things like:
  `work-in-progress`, `wip`, etc.
- Label Bot can mark a pull requests with additional tags based on glob patterns. If a file matches a glob pattern, it
  is assigned the associated label(s).

## Can I Use It?

Sure, you'll need to fork it and deploy it on Heroku, or host it somewhere else if desired. There is no publicly
available bot on the marketplace.

1. Make sure to set the `GH_BOT` environmental variable in your environment. `GH_BOT` should be the name of the
   GitHub user the bot is operating as.
2. Also make sure you set `GH_AUTH` variable which is the access token by which the bot user is authenticated.
   Normally `repo` privileges are sufficient. Learn how to setup an [access token][access] by checking out the
   documentation.
3. Setup a webhook in your repository. Point the URL to your running app. Ensure it sends data via JSON. Use a
   token with high entropy and make sure it is used by your webhook and assigned to `GH_SECRET` in your app
   environment. Lastly, make sure the webhook sends requests for `issues`, `push`, and `pull_request` events.
4. If you are using a separate bot account to communicate with your repos, you may have to add the bot as a
   collaborator.

## Triage Labels

Label Bot will mark new issue with `triage` and new pulls with `needs-review`. In addition, when a pull request is
pushed with new changes, they are also marked with `needs-review`.

If desired, one can control what label/labels get assigned on these two events by adding the following options to their
`.github/labels.yml` in their project:

```yml
triage_issue_labels: [triage]
triage_pull_request_labels: [needs-review]
```

## WIP Labels

Label Bot can mark a pull request as pending if certain labels are present. Simply provide a list in the YAML file at
`.github/labels.yml` to configure it:

```yml
wip:
  - work-in-progress
  - needs-review
  - needs-decision
  - needs-confirmation
  - requires-changes
  - rejected
```

By default, Label Bot looks for one of the following: `wip`, `work in progress`, or `work-in-progress`.

## Wildcard Labels

Wildcard labels is a feature that labels pull requests based on file patterns of changed files. It uses the Python
library [`wcmatch`][wcmatch] to perform the file matching.

By default, [`wcmatch`][wcmatch] is configured with the following flags:

- [SPLIT][split]: enables chaining multiple patterns together with `|` so they are evaluated together. For instance, if
  we wanted to find all Markdown and HTML files in a folder, we could use the following pattern:

    ```
    folder/*.md|folder/*.html
    ```

- [GLOBSTAR][globstar]: enables the pattern `**` to match zero or more folders. For instance, if we wanted to find
  Python files under any child folder of a given folder:

    ```
    src/**/*.py
    ```

- [DOTGLOB][dotglob]: enables the matching of `.` at the start of a file in patterns such as `*`, `**`, `?` etc. Since
  this is enabled, we should be able to match files that start with `.` like `.travis.yml` by simply using `*`.

- [NEGATE][negate]: allows inverse match patterns by starting a pattern with `!`. It is meant to filter other normal
  patterns. For instance if we wanted to find all Python files except those under our *tests* folder:

    ```
    **/*.py|!tests/**
    ```

- [NEGATEALL][negateall]: allows using inverse patterns when no normal patterns are given. When an inverse pattern is
  given with no normal patterns, the pattern of `**` is assumed as the normal pattern to filter. So if we wanted find
  any file accept HTML files:

  ```
  !*.html
  ```

Check out the libraries [documentation][glob] for more information on syntax.

The configuration file should be in the YAML format and should be found at `.github/labels.yml`. The rules consist of
two parts: flags that control the behavior of the glob patterns, and rules that define pattens of modified files that
must match for the associated label to be applied.

There are three global flags that alter the default behavior of the glob patterns:

Flag                             | Description
-------------------------------- | -----------
[`brace_expansion`][brace]       | Allows Bash style brace expansion in patterns: `a{b,{c,d}}` → `ab ac ad`.
[`extended_glob`][extglob]       | Enables Bash style extended glob patterns: `@(ab\|ac\|ad)`, etc. When this is enabled, the flag [`MINUSNEGATE`][minusnegate] is also enabled. `MINUSNEGATE` changes inverse patterns to use `-` instead of `!` to avoid conflicts with the extended glob patterns of `!(...)`.
[`case_insensitive`][ignorecase] | As the action is run in a Linux environment, matches are case sensitive by default. This enables case insensitive matching.

Global flags are placed at the top of the configuration file:

```yml

case_insensitive: true

rules:
  - labels: [python, code]
    patterns:
    - '**/*.py'
    - '**/*.pyc'
```

`rules` should contain a list of patterns coupled with associated to labels to apply. Both the `labels` key and the
`patterns` key should be lists.

For each entry in a `patterns` list are handled independently from the other patterns in the list. So if we wanted to
augment a normal pattern with an inverse pattern, we should use `|` on the same line:

```yml
rules:
  - labels: [python, code]
    patterns:
    - '**/*.py|!tests'  # Any Python file not under tests
```

Having these patterns on different lines will **not** provide the same behavior as they will be evaluated independently.

```yml
rules:
  - labels: [python, code]
    patterns:
    - '**/*.py'  # All Python files
    - '!tests'   # Any file not under tests
```

[wcmatch]: https://github.com/facelessuser/wcmatch
[split]: https://facelessuser.github.io/wcmatch/glob/#globsplit
[globstar]: https://facelessuser.github.io/wcmatch/glob/#globglobstar
[dotglob]: https://facelessuser.github.io/wcmatch/glob/#globdotglob
[negate]: https://facelessuser.github.io/wcmatch/glob/#globnegate
[negateall]: https://facelessuser.github.io/wcmatch/glob/#globnegateall
[minusnegate]: https://facelessuser.github.io/wcmatch/glob/#globminusnegate
[extglob]: https://facelessuser.github.io/wcmatch/glob/#globextglob
[brace]: https://facelessuser.github.io/wcmatch/glob/#globbrace
[ignorecase]: https://facelessuser.github.io/wcmatch/glob/#globignorecase
[glob]: https://facelessuser.github.io/wcmatch/glob/


## Label Management

A simple label manager that syncs labels in a YAML at `.github/labels.yml` on the master branch of your project. Labels
are either added if they don't exist, or edited if they do exist and the description or color have changed. Optionally,
labels not in the list will be deleted if `mode` is set to `delete` (default is `normal`).

Labels are stored in a list in the configuration file:

```js
labels:
- name: bug
  color: bug
  description: Bug report.

- name: feature
  color: feature
  description: Feature request.

```

You can also predefine color variables. This is useful if you wish to reuse a color for multiple labels.

```js
colors:
  bug: '#c45b46'
  feature: '#7b17d8'

labels:
- name: bug
  color: bug
  description: Bug report.

- name: feature
  color: feature
  description: Feature request.
```

You can also specify a label to be renamed. This is useful if you want to change the name of a label that is present on
existing issues. Simply create an entry using the the new name, and add the old named under `renamed`. So if we had
a label called `bug`, and we wanted to add a :bug: emoji to the name:

```js
labels:
- name: 'bug :bug:'
  renamed: bug
  color: bug
  description: Bug report.
```

When `delete_labels` is set to `true`, labels not explicitly defined are remove. While you can certainly define those
labels so that they are in the list, you can also just add the to the ignore list. Maybe they are labels created by an
external process like `dependbot`. Regardless, if you have existing labels that you do not want to explicitly define,
and do not wish to lose them, you can add them to the ignore lsit:

```js
colors:
  bug: '#c45b46'

ignores:
- dependencies
- security

labels:
- name: bug
  color: bug
  description: Bug report.

- name: feature
  color: feature
  description: Feature request.
```

[license-image-mit]: https://img.shields.io/badge/license-MIT-blue.svg
[github-ci-image]: https://github.com/gir-bot/label-bot/workflows/build/badge.svg
[github-ci-link]: https://github.com/gir-bot/label-bot/actions?workflow=build
