from enum import Enum


class REQ(Enum):
    NETWORK_CHECK = "network_check"
    REGISTER_BOARD = "register_board"
    UPDATE_BOARD = "update_board"
    CHECK_CONNECTION = "check_connection"
    CHECK_MAC = "check_mac"
    GET_CITIES = "get_cities"
    GET_TOWNS = "get_towns"
    GET_SCHOOLS = "get_schools"
    GET_SCHOOL_WITHOUT_LIMIT = "get_school_without_limit"
    CHECK_SCHOOL_CODE = "check_school_code"
    SEARCH_SCHOOL = "search_school"
    GET_CITIES_FOR_CODE = "get_cities_for_code"
    GET_TOWNS_FOR_CODE = "get_towns_for_code"
