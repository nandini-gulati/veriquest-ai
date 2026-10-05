"""Task modules used by the optional development and data-preparation CLI.

The web application imports only ``tasks.defaults``.  Keeping this package
initializer empty prevents the production web service from importing Docker,
benchmarking, and local-vector-search tooling that it never uses.
"""
