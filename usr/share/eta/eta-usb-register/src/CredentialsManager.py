import string
import random
import binascii
import pickle
import json


def save_credentials_file(credentials_file, credentials_obj):
    try:
        text = json.dumps(credentials_obj)
        hexlified = binascii.hexlify(text.encode("utf-8"))
        with open(credentials_file, "wb") as f:
            pickle.dump(hexlified, f, pickle.HIGHEST_PROTOCOL)
            f.write(hexlified)
            f.flush()
    except Exception as e:
        print(e)
        return (False, e)

    return (True, "")


def generate_random_password():
    """
    Generates a random 8-character password for the user
    """
    length = 8
    characters = string.ascii_letters + string.digits  # + '!#$&' string.punctuation
    password = "".join(random.choice(characters) for i in range(length))

    return password


def turkish_to_english(text):
    """
    Converts Turkish characters to English characters
    """
    replacements = {
        # Â
        "â": "a",
        "Â": "A",
        # Ç
        "ç": "c",
        "Ç": "C",
        # Ğ
        "ğ": "g",
        "Ğ": "G",
        # ı
        "ı": "i",
        "î": "i",
        "İ": "I",
        "Î": "I",
        # ö
        "ö": "o",
        "ô": "o",
        "Ö": "O",
        "Ô": "O",
        # ş
        "ş": "s",
        "Ş": "S",
        # ü
        "ü": "u",
        "Ü": "U",
        "Û": "U",
        "û": "u",
    }

    # Remove trailing spaces
    text = text.strip()

    # Replace Turkish Chars
    for tr_char, en_char in replacements.items():
        text = text.replace(tr_char, en_char)

    # Remove non ascii chars
    text = "".join([char for char in text if char.isalnum() or char == " "])

    # Replace " "
    text = text.lower().replace(" ", ".")

    return text
