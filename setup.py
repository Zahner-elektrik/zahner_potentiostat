import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setuptools.setup(
    name="zahner_potentiostat",
    version = "1.0.5",
    author="Maximilian Krapp",
    author_email="maximilian.krapp@zahner.de",
    description="Library to control Zahner Potentiostats.",
    keywords=["potentiostat, electrochemistry, chemistry, eis, cyclic voltammetry, fuel-cell, battery"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://zahner.de/",
    project_urls={
        "Documentation": "http://zahner.de/documentation/zahner_potentiostat/index.html",
        "Bug Tracker": "https://github.com/Zahner-elektrik/zahner_potentiostat/issues",
        "Source Code": "https://github.com/Zahner-elektrik/zahner_potentiostat",
    },
    packages=setuptools.find_packages(where="."),
    license = "MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",

        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
        
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    platforms="any",
)
