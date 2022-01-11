try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from keepsake_ui import __version__


requirements = ["gunicorn~=20.1.0", "keepsake~=0.4.2", "flask~=2.0.2"]

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="keepsake_ui",
    version=__version__,
    description="Web UI to keepsake tool.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Jakub Semric",
    author_email="jakubsemric@gmail.com",
    url="https://github.com/jsemric/keepsake-ui",
    packages=[
        "keepsake_ui",
    ],
    package_dir={"keepsake_ui": "keepsake_ui"},
    include_package_data=True,
    package_data={"": ["templates/*"]},
    install_requires=requirements,
    license="Apache License 2.0",
    python_requires=">=3.6.0",
    test_suite="tests",
    entry_points={
        "console_scripts": [
            "keepsake-ui=keepsake_ui.main:main",
        ],
    },
)
