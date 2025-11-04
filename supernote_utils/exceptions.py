"""Custom exceptions for supernote-utils"""


class SupernoteUtilsError(Exception):
    """Base exception for all supernote-utils errors"""
    pass


class ProviderError(SupernoteUtilsError):
    """Error related to LLM provider operations"""
    pass


class ProviderNotAvailableError(ProviderError):
    """Provider is not available or not configured"""
    pass


class ProviderAPIError(ProviderError):
    """Error from provider API"""
    pass


class ImageProcessingError(SupernoteUtilsError):
    """Error processing images"""
    pass


class FileFormatError(SupernoteUtilsError):
    """Error with file format"""
    pass


class ConfigurationError(SupernoteUtilsError):
    """Error with configuration"""
    pass
