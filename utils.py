"""Utility functions for the Gunter application."""

from typing import Any, Dict, List, Union


def filter_names_by_lang(
    data: Union[Dict[str, Any], List[Any]], lang_code: str, fallback_lang: str = "en"
) -> Union[Dict[str, Any], List[Any], Any]:
    """
    Recursively processes a dictionary or list to replace 'names' dictionaries
    with a single 'name' field for the specified language.

    Args:
        data: The data structure to process.
        lang_code: The preferred language code (e.g., 'de', 'en').
        fallback_lang: The fallback language code if the preferred is not available.

    Returns:
        The processed data structure with 'names' replaced by 'name'.
    """
    if isinstance(data, dict):
        if "names" in data and isinstance(data["names"], dict):
            names = data["names"]
            selected_name = (
                names.get(lang_code)
                or names.get(fallback_lang)
                or next(iter(names.values()), None)
            )
            new_dict: Dict[str, Any] = {
                k: filter_names_by_lang(v, lang_code, fallback_lang)
                for k, v in data.items()
                if k != "names"
            }
            if selected_name:
                new_dict["name"] = selected_name
            return new_dict
        return {
            k: filter_names_by_lang(v, lang_code, fallback_lang)
            for k, v in data.items()
        }

    if isinstance(data, list):
        return [filter_names_by_lang(item, lang_code, fallback_lang) for item in data]

    return data
