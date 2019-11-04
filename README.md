[![Build][github-ci-image]][github-ci-link]
![License][license-image-mit]
# Label Bot

## Overview

This is a GitHub app for performing label related actions in a repository. It is written by and used in projects for
[@facelessuser](https://github.com/facelessuser). It uses the the persona of [@gir-bot](https://github.com/gir-bot), but
can technically use any user. Label Bot is not a publicly available service, but can be modified and installed for
personal use in Heroku or some other hosting service. Python 3.6+ is required.

Label bot handles a handful of label related scenarios:

- Label Bot can manage labels by syncing them up with a list specified in a configuration file. If the configuration
  file changes, labels will be added, edited, or removed (if enabled) from your repository to match the configuration.
  This modifies the global issue list for your repository.
- Label Bot can mark new issues with a specific labels. For instance, out of the box, it marks new issues with `triage`.
  It can also remove labels if desired.
- Label Bot can mark new pull requests and pushes to a pull requests with specific labels. For instance, out of the box,
  it will mark new pull requests and new pushes to the pull request with `needs-review`. It can also remove remove
  labels if desired. This can come in handy if you've (for example) added an `approved` label and more changes were
  pushed, it could remove the `approved` label, and then add `needs-review`.
- Label Bot will mark pull requests as pending if certain labels are present. By default it looks for things like:
  `work-in-progress`, `wip`, etc.
- Label Bot can tag a pull requests with additional labels based on glob patterns. If a file matches a glob pattern, it
  is assigned the associated label(s).
- Label Bot also exposes commands to retrigger tasks, sync labels, and other specialty label related commands.

## Can I Use It?

Sure, you'll need to fork it and deploy it on Heroku, or host it somewhere else if desired. There is no publicly
available bot on the marketplace.

1. Make sure to set the `GH_BOT` environmental variable in your environment. `GH_BOT` should be the name of the
   GitHub user the bot is operating as.
2. Also make sure you set `GH_AUTH` variable which is the access token by which the bot user is authenticated.
   Normally `repo` privileges are sufficient. Learn how to setup an [access token][access] by checking out the
   documentation.
3. Setup a webhook in your repository. Point the URL to your running app. Ensure it sends data via JSON. Use a
   token with high entropy and make sure it is used by your webhook, but also assigned to `GH_SECRET` in your app's
   environmental variables. Lastly, make sure the webhook sends requests for:

    - `issues`: allows triage labels task to be sent events.
    - `push`: , allows the repository label sync task to be sent events.
    - `pull request`: allows the the WIP, review, and pull request auto label task to be sent events.
    - `issue comments`: allows the ability to retrigger tasks via mentions to the bot through issues.

4. If you are using a separate bot account to communicate with your repos, you may have to add the bot as a
   collaborator.

[access]: https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line

## Which Configuration Gets Used?

[Sync](#sync) commands, which occur on pushes to master and via `@bot sync labels` commands in pull request and issues,
are always run using the configuration file on `master`.

For issues, the configuration on master gets used as there is no configuration associated with an issue.

For pull requests, the configuration file in the pull gets used except when issuing a [sync](#sync) command.

All commands issued in the body of a pull request, issue, or comment in an issue or pull request are restricted to
owners and collaborators.

## Using a Configuration Template

You can use a configuration template file and share it across repositories. This is a good way to define common labels
that you wish to reuse. You can set the template to use in your local repository file in `.github/labels.yml`. In our
case it is `facelessuser:master-labels:labels.yml:master`.

When merging the template configuration and the local repo configuration, merging will occur as follows:

- keys that contain string or bool will override the template with the local value.
- keys that contain list values will append the local list to the template list.
- keys that contain hash values will append the key value pair of the local to the template. In the case of duplicates,
  the local will override.
- One exception is with `lgtm_add`. The keys `pull_request` and `issue` will append values from the local to the
  template. In the future, `lgtm_add` may get broken up into two separate options for consistency. This would not occur
  until version 2.0.

If either the template or local configuration file fails to be acquired, an empty set of options will be returned. Since
repository label syncing will not occur when the `labels` option is missing, this will prevent all your repository
labels from getting wiped out in the case of a failure.

## Triage Labels

Label Bot will mark new issue with `triage`.

If desired, you can control what label gets assigned by adding the following option in `.github/labels.yml` in your
project:

```yml
triage_label: triage
```

If you want to turn off triage, because you are creating the issue and have a good understanding of it, you can attach
the `skip-triage` label. If you prefer to rename it or add additional labels, simply specify a different name(s) using
the following option:

```yml
triage_skip: [skip-triage]
```

If you'd like to remove labels when running the command triage as well, you can use the `triage_remove` option. This is
good if you need to but it back in the triage state via a retrigger and reset some labels.

```yml
triage_remove: [confirmed]
```

## Review Labels

Label Bot will mark new pull requests with `needs-review`. It will also re-add the label if it was removed, and more
code is pushed.

If desired, you can control what label gets assigned by adding the following option in `.github/labels.yml` in your
project:

```yml
review_label: needs-review
```

If you want to turn off this feature in a pull request, for whatever reason, you can attach the `skip-review` label. If
you prefer to rename it, or add additional labels, simply specify a different name(s) using the following option:

```yml
review_skip: [skip-review]
```

If you'd like to also remove labels, such as `approved` labels, you can configure the `review_remove` option and list
various labels to remove.

```
review_remove: [approved]
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

- [`SPLIT`][split]: enables chaining multiple patterns together with `|` so they are evaluated together. For instance,
  if we wanted to find all Markdown and HTML files in a folder, we could use the following pattern:

    ```
    folder/*.md|folder/*.html
    ```

- [`GLOBSTAR`][globstar]: enables the pattern `**` to match zero or more folders. For instance, if we wanted to find
  Python files under any child folder of a given folder:

    ```
    src/**/*.py
    ```

- [`DOTGLOB`][dotglob]: enables the matching of `.` at the start of a file in patterns such as `*`, `**`, `?` etc. Since
  this is enabled, we should be able to match files that start with `.` like `.travis.yml` by simply using `*`.

- [`NEGATE`][negate]: allows inverse match patterns by starting a pattern with `!`. It is meant to filter other normal
  patterns. For instance if we wanted to find all Python files except those under our *tests* folder:

    ```
    **/*.py|!tests/**
    ```

- [`NEGATEALL`][negateall]: allows using inverse patterns when no normal patterns are given. When an inverse pattern is
  given with no normal patterns, the pattern of `**` is assumed as the normal pattern to filter. So if we wanted find
  any file accept HTML files:

  ```
  !*.html
  ```

Check out the libraries [documentation][glob] for more information on syntax.

The configuration file should be in the YAML format and should be found at `.github/labels.yml`. The rules consist of
two parts: flags that control the behavior of the glob patterns, and rules that define patterns of modified files that
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
and do not wish to lose them, you can add them to the ignore list:

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

## Commands

Commands can be initiated in either the issue/pull request body, or comments in an issue/pull request. It is recommended
to have bot commands on their own line separated from other content with a new line, but they will be scraped no matter
where they are found. They are scraped from the rendered markdown. Commands that apply to open issues will not execute
if the issue is closed.

### Retrigger

You can force the bot to retrigger checks by commenting in issues. If a task failed for some reason you can rerun by
mentioning the bot's name, and then asking it to retrigger:

```
@bot retrigger auto-labels
```

If you want to rerun all checks, you can ask it to run `all`:

```
@bot retrigger all
```

Available checks that can be retriggered are: `wip`, `review`, `triage`, and `auto-label`. `triage` cannot be run in
pull requests, and the other are not run outside of pull requests.

### Sync

If desired, you can also resync the labels on demand with the following command:

```
@bot sync labels
```

This will cause the repository's labels to be synced with the `.github/labels.yml` file on `master`.

### LGTM

LGTM (looks good to me) is a command that is meant for transitioning an issue into an accepted state. This often means
removing labels and maybe even adding new labels. The idea is that by stating the issue "looks good", you are indicating
that no additional information is needed to understand the bug or feature request, and in the case of pull requests,
that no additional work is needed.

For instance, we may have an issue tagged with `triage`. Once we've evaluated it and determined that it is descriptive
enough, we may want to accept it by removing the `triage` label.

In the configuration file we simply specify when `lgtm` is run that we want to remove tags such as `triage`:

```yml
lgtm_remove:
  - triage
```

Then we can simply run the following command in the issue's comments:

```
@bot lgtm
```

Let's say we have a pull request, and we want to clear `needs-review` label, but also tag it with the label `approved`.
We can simply create the `lgtm_remove` (which is shared for both pull requests and issues), and then use the `lgtm_add`
option to specify the desired labels to add under the key `pull_request` (if specifying for a normal issue, we'd use
`issue`).

```yml
lgtm_remove:
  - needs-review

lgtm_add:
  pull_request: [approved]
```

Then when we run `@bot lgtm`, `needs-review` will be removed, and `approved` will be added.

### Add and Remove

You can add or remove labels with the commands `@bot add label-name` or `@bot remove label-name`. You can specify
multiple labels by separating them with comas: `@bot add Documents, Core Code`.

[license-image-mit]: https://img.shields.io/badge/license-MIT-blue.svg
[github-ci-image]: https://github.com/gir-bot/label-bot/workflows/build/badge.svg
[github-ci-link]: https://github.com/gir-bot/label-bot/actions?workflow=build
