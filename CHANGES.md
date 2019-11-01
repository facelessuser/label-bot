# Changelog

## 1.3.1

- **FIX**: Ensure that configuration failures cause a task to fail.
- **Fix**: Index all repository labels before modifying the repository labels.

## 1.3.0

- **NEW**: Optionally allow specifying a master configuration file template from another repository.
- **FIX**: Only collaborators and owners are allowed to issue commands.
- **FIX**: Fix commands not working in pull request issue body.
- **FIX**: Throttle sync command more in cases where the API is being hit quite hard.

## 1.2.0

- **NEW**: Add `@bot lgtm` command to remove blocking labels and optionally add others.
- **NEW**: Allow `triage` and `review` task to remove labels as well.
- **NEW**: Add `@bot add` and `@bot remove` command to bulk add or remove labels.
- **FIX**: Avoid running retrigger commands on a closed issue.
- **FIX**: Fix issue with deleting labels in wildcard labels.

## 1.1.3

- **FIX**: Internal cleanup for easier maintenance.
- **FIX**: Wildcard labels should always get live labels. And should set labels and/or remove labels as required instead
  of overwriting all labels. This will prevent any chance of accidentally remove unintended labels.

## 1.1.2

- **FIX**: Bad default when `labels` key is not found in configuration file.
- **FIX**: Bad comparison in `triage` and `review` task when comparing labels.
- **FIX**: Bad extraction of labels when extracting from `issues` event.

## 1.1.1

- **FIX**: Fix regression with triage.
- **FIX**: Fix triage message not posting on error.
- **FIX**: Fix commands not being parsed in opening of an issue.
- **FIX**: Handling of labels quickly across tasks executed at the same time.

## 1.1.0

- **NEW**: Allow re-triggering pull and issue tasks if something went wrong. This is done with commands in the issues.
- **FIX**: Fix issue where label that has been renamed, and the sync script is run again, the renamed value will get
  removed.

## 1.0.1

- **Fix**: Fix issues with rate limit abuse. Long running tasks should be marked pending and then deferred. Also, with
  big batches of commands, we should sleep for 1 second between requests.

## 1.0.0

- **NEW**: Official release.
