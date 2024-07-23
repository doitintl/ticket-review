from google.auth.transport import requests
from streamlit.web.server.websocket_headers import _get_websocket_headers
from google.oauth2 import id_token


def validate_iap_jwt(iap_jwt, expected_audience):
    """Validate an IAP JWT.

    Args:
      iap_jwt (str): The contents of the X-Goog-IAP-JWT-Assertion header.
      expected_audience (str): The Signed Header JWT audience. See
          https://cloud.google.com/iap/docs/signed-headers-howto
          for details on how to get this value.

    Returns:
      Tuple[str, str, str]: A tuple containing the user_id, user_email, and error_str.
    """

    try:
        decoded_jwt = id_token.verify_token(
            iap_jwt,
            requests.Request(),
            audience=expected_audience,
            certs_url="https://www.gstatic.com/iap/verify/public_key",
        )
        return (decoded_jwt["sub"], decoded_jwt["email"], "")
    except Exception as error:
        return (None, None, f"**ERROR: JWT validation error {error}**")


def user_details():
    """ 
        Getting all user detials from headers
    """

    headers = _get_websocket_headers()
    access_token = headers.get("X-Goog-Iap-Jwt-Assertion")
    user_id, user_email, error_str = validate_iap_jwt(
        access_token, "/projects/874764407517/global/backendServices/2612614375736935637")
    return user_id, user_email, error_str


def find_fa_by_email(client_fb, email):
    """
    Fetch a document from a Firestore collection where the email attribute matches a specific value.
    Throws an error if more than one document matches the query.

    Args:
      client_fb (google.cloud.firestore.Client): The Firestore client object.
      email (str): The email value to match in the Firestore collection.

    Returns:
      An array containing a single dictionary with the data of the matching document.
      Throws an error if more than one document is found.
    """
    query_ref = client_fb.collection("cre").where("email", '==', email)
    documents = query_ref.stream()

    results = []
    for doc in documents:
        results.append(doc.to_dict())
        if len(results) > 1:
            raise ValueError(
                "More than one document found for the provided email.")

    return results
