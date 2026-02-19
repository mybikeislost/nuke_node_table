from setuptools import setup, find_packages

setup(
    name="node_table",
    packages=find_packages(),

    setup_requires=['setuptools_scm'],
    python_requires='>=2.7,<4',

    package_data={
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.txt', '*.rst'],
    },

    # metadata to display on PyPI
    author="Mitja Mueller-Jend",
    author_email="mitja.muellerjend@gmail.com",
    description="Spreadsheet showing and editing knobs of selected Nodes.",
    license="MIT",
    keywords="nuke nodes knobs multi node editor",
    url="https://github.com/mybikeislost/nuke_node_table",
    project_urls={
        "Bug Tracker": "https://github.com/mybikeislost/nuke_node_table/issues",
        "Source Code": "https://github.com/mybikeislost/nuke_node_table",
        "Upstream": "https://gitlab.com/filmkorn/nuke_node_table",
    },

    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Pick your license as you wish (should match "license" above)
         'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.7',
    ],

    use_scm_version = True,
)
