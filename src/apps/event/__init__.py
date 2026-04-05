"""Event app package.

Keep package imports side-effect free so repository and request imports do not
eagerly import routers and trigger circular dependencies.
"""
