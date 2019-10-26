# Changelog

## 1.0.1

- **Fix**: Fix issues with rate limit abuse. Long running tasks should be marked pending and then deferred. Also, with
  big batches of commands, we should sleep for 1 second between requests.

## 1.0.0

- **NEW**: Official release.
