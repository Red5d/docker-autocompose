from setuptools import setup, find_packages
setup(
    name = "docker-autocompose",
    version = "1.2.0",
    description = "Generate a docker-compose yaml definition from a running container",
    url = "https://github.com/Red5d/docker-autocompose",
    author = "Red5d",
    license = "GPLv2",
    keywords = "docker yaml container",
    packages = find_packages(),
    install_requires = ['pyaml>=17.12.1', 'docker>=3.4.1'],
    scripts = ['autocompose.py'],
    entry_points={
        'console_scripts': [
            'autocompose = autocompose:main',
        ]
    }
)
