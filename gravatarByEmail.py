def get_gravatar(email):
    """
    Takes in an email, returns a gravatar link

    :param email: email to be gravatared
    :return: hyperlink
    """
    import hashlib
    BASE_URI = "https://www.gravatar.com/avatar"
    # Trim whitespace and lower case
    trimmed_lower_email = email.lower().strip()
    # Make md5
    md5_email = hashlib.md5(trimmed_lower_email.encode("utf-8")).hexdigest()

    return f"{BASE_URI}/{md5_email}"
