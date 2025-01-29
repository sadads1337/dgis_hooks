
g_supported_cpp_file_extensions = {".cpp", ".c", ".inl", ".h", ".hpp", ".hqt"}


def is_supported_cpp_file_extension(ext: str) -> bool:
    return ext in g_supported_cpp_file_extensions
