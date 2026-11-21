# Repository Maintenance Safety

## Corruption repair utility

The utility at tools/fix_corruption.py is a repository-maintenance helper. It is not part of the Bio-Research analysis runtime and must not be used against research datasets, backups, databases, credentials, or deployed files.

### Safe operating contract

- Default invocation is read-only dry-run. It reports candidate edits and does not write source files or create backups.
- Applying changes requires the explicit --apply flag.
- Each changed source file receives an adjacent .bak backup created with exclusive file creation and restrictive mode 0600 where supported. Existing backups are never overwritten.
- The source is written through a temporary file in the same directory and atomically replaced only after the backup has been flushed and the source identity/content have been rechecked.
- Original file mode and byte-level line endings are preserved.
- Symlinks and hard-linked files are skipped. Invalid UTF-8 is rejected rather than decoded with replacement characters.
- If a backup cannot be created, the source is not changed. If atomic replacement fails, the original remains and the backup is retained for recovery.
- Paths printed by the utility are JSON-quoted to prevent terminal/log line injection. They remain local filesystem metadata and should stay in trusted operator channels.

### Recommended procedure

1. Use an isolated worktree or disposable copy of the repository.
2. Run the default dry-run and inspect every proposed candidate.
3. Confirm the target files are ordinary, single-link UTF-8 source files and that no adjacent .bak backup already exists.
4. Run with --apply only after reviewing the dry-run.
5. Review the resulting source diff and run the repository's tests.
6. Retain the .bak files under the repository's approved maintenance/retention policy. Do not commit or publish backups.

### Automated safety coverage

The focused CI suite exercises dry-run non-mutation, exact backup preservation, restrictive backup permissions on POSIX, existing-backup refusal, invalid UTF-8 refusal, symlink and hard-link refusal, atomic-replacement failure recovery, CRLF preservation, and JSON-quoted path output.

These tests use temporary synthetic files only. They do not authorize running the utility against the production repository or any research data.
