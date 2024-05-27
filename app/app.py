import streamlit as st
from streamlit.web.server.websocket_headers import _get_websocket_headers
from google.auth.transport import requests
from google.oauth2 import id_token


def validate_iap_jwt(iap_jwt, expected_audience):
    """Validate an IAP JWT.

    Args:
      iap_jwt: The contents of the X-Goog-IAP-JWT-Assertion header.
      expected_audience: The Signed Header JWT audience. See
          https://cloud.google.com/iap/docs/signed-headers-howto
          for details on how to get this value.

    Returns:
      (user_id, user_email, error_str).
    """

    try:
        decoded_jwt = id_token.verify_token(
            iap_jwt,
            requests.Request(),
            audience=expected_audience,
            certs_url="https://www.gstatic.com/iap/verify/public_key",
        )
        return (decoded_jwt["sub"], decoded_jwt["email"], "")
    except Exception as e:
        return (None, None, f"**ERROR: JWT validation error {e}**")

def main():

    headers = _get_websocket_headers()
    access_token = headers.get("x-goog-iap-jwt-assertion")

    st.title('Ticket Review App')

    # Text area for ticket input
    ticket_text = st.text_area('Headers', headers)

    ticket_text = st.text_area('Ticket Text', 'Enter the ticket text here...')

    # Text area for reviewer's thoughts
    reviewer_thoughts = st.text_area('Your Thoughts', 'Enter your thoughts here...')

    # Star rating
    star_rating = st.slider('Star Rating', 1, 5)

    # Checkboxes
    good_story = st.checkbox('This is a good story')
    needs_cre_feedback = st.checkbox('Needs a cre-feedback')

    # Button to submit review
    if st.button('Submit Review'):
        st.write('Review Submitted:')
        st.write('Ticket Text:', ticket_text)
        st.write('Your Thoughts:', reviewer_thoughts)
        st.write('Star Rating:', star_rating)
        st.write('This is a good story:', good_story)
        st.write('Needs a cre-feedback:', needs_cre_feedback)

if __name__ == "__main__":
    main()