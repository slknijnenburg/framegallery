"""
Pluggable photo libraries.

This package provides a source-agnostic abstraction (:class:`~framegallery.libraries.base.Library`)
that lets the slideshow draw photos from multiple backends: the local filesystem gallery and
external services such as Immich. The :class:`~framegallery.libraries.manager.LibraryManager`
blends across all enabled libraries.
"""
