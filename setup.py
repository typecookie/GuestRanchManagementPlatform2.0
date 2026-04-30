from setuptools import setup, find_packages

setup(
    name="guest-ranch-management-platform",
    version="0.1.0-beta1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Django>=5.0",
        "gunicorn",
        "whitenoise",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "guest-ranch-manage=manage:main",
        ],
    },
)
