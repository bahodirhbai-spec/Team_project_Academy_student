"""All configurable values of the application, in one folder.

- settings.py        where the app runs (.env, port, paths) - outer
- business_rules.py  rules of the problem (scores, statuses) - inner

This file deliberately imports nothing: Python runs it whenever any
module in this folder is imported, so an import here would make the
business rules load the settings (and .env) too.
"""
