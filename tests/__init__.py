"""RWB test package.

The ``__init__.py`` makes the repository's ``tests`` directory a regular
package so ``from tests.execution_fixtures import ...`` style imports resolve
here instead of colliding with unrelated ``tests`` packages installed in
site-packages.
"""
