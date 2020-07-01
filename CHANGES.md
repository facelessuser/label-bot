# Changelog

## 1.9.0

- **NEW**: Allow `minus_negate` logic to be disabled as there is no longer a conflict with `NEGATE` and `EXTGLOB`.

## 1.8.0

- **NEW**: Update to latest `gidgethub`, `pyyaml`, and `beautifulsoup4`.
- **NEW**: Add environment variable `GH_BOT_LINK` to specify the link for when status is clicked.

## 1.7.0

- **NEW**: More logging and specify which module is logging along with repository/user where the request originated
  from.

## 1.6.0

- **NEW**: Bot should allow `add` and `remove` commands in issue comments to modify labels even if the issue is closed.

## 1.5.0

- **NEW**: New command added called `retrigger-local` which will force a pull request retrigger to use the configuration
  in the pull request reference instead of using `master`. This is great if you want to test changes to the label
  configuration in a pull request.
- **NEW**: Configuration file is always read from `master` except when `retrigger-local` is run in a pull request.
- **FIX**: Labels that were renamed are not always detected as renamed.
- **FIX**: Better logic to avoid adding a label that already exists or removing a label that does not exist. Also,
  detect such failures if we do run into such scenarios, and don't fail the sync.
- **FIX**: Case logic when comparing triage and review labels.

## 1.4.0

- **NEW**: Add options `lgtm_add_issue` and `lgtm_add_pull_request` that are meant to replace `lgtm_add`. The old
  `lgtm_add` will be mapped to the new options and handled internally. `lgtm_add` will be removed in version 2.0.

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
