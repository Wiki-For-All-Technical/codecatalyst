# TODO: Fix Session Expiration Issue

## Tasks
- [x] Update `config.py` to add explicit session lifetime configuration.
- [x] Fix `auth/wiki.py` to ensure session data persists by adding `session.modified = True` in `finish_login`.

## Followup Steps
- [x] Test the application to ensure sessions persist and metadata is retained during the upload process.
- [x] Verify that the "Session expired. Please select images again." message no longer appears under normal usage.
