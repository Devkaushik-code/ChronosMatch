from setuptools import Extension, setup
from Cython.Build import cythonize

extensions = [
    Extension(
        "chronosmatch.matching_engine_cython",
        ["src/chronosmatch/matching_engine_cython.pyx"],
    )
]

setup(
    name="chronosmatch-cython",
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
    ),
    package_dir={"": "src"},
    packages=["chronosmatch", "chronosmatch.ipc"],
)
