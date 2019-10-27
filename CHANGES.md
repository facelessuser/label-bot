# Changelog

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
