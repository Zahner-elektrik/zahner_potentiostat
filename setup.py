import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setuptools.setup(
    name="zahner_potentiostat",
    version = "1.0.8",
    author="Maximilian Krapp",
    author_email="maximilian.krapp@zahner.de",
    description="Library to control Zahner Potentiostats.",
    keywords=["potentiostat, electrochemistry, chemistry, eis, cyclic voltammetry, fuel-cell, battery"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://zahner.de/",
    project_urls={
        "Documentation": "https://doc.zahner.de/zahner_potentiostat/index.html",
        "Examples": "https://github.com/Zahner-elektrik/Zahner-Remote-Python",
        "Source Code": "https://github.com/Zahner-elektrik/zahner_potentiostat",
        "Bug Tracker": "https://github.com/Zahner-elektrik/zahner_potentiostat/issues",
    },
    packages=setuptools.find_packages(where="."),
    license = "MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",

        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "Intended Audience :: Manufacturing",
        
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
        
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    platforms="any",
)
