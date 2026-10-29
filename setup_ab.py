from setuptools import Extension, setup
from Cython.Build import cythonize

extensions = [
    Extension(
        "chronosmatch.matching_engine_cython_original",
        ["src/chronosmatch/matching_engine_cython_original.pyx"],
    ),
    Extension(
        "chronosmatch.matching_engine_cython_optimized",
        ["src/chronosmatch/matching_engine_cython_optimized.pyx"],
    ),
]

setup(
    name="chronosmatch-ab-test",
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
    ),
    package_dir={"": "src"},
    packages=["chronosmatch", "chronosmatch.ipc"],
)
