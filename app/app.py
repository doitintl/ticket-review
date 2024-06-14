import datetime
import streamlit as st
from google.cloud import bigquery
from google.cloud import firestore
from google.cloud import firestore_admin_v1
from google.api_core.exceptions import GoogleAPICallError
from streamlit_extras.tags import tagger_component
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

st.set_page_config(
    page_title="Ticket Review App",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

PROJECT = "doit-ticket-review"

client = bigquery.Client()
client_fb = firestore_admin_v1.FirestoreAdminClient()
db = firestore.Client(project=PROJECT)

@st.cache_data
def get_ticket(ticket_id):
    """ 
        Getting Ticket data from a BigQuery dataset. 
    """

    try:
        query = f'SELECT *EXCEPT(comment) FROM `doit-ticket-review.sample_data.v1`, UNNEST(comment) as c WHERE id = {ticket_id}'
        query_job = client.query(query)
        results = query_job.result()  # Waits for the query to complete
        return results.to_dataframe()

    except GoogleAPICallError as e:
        st.error(f"API Error: {e}")
        return e

def main():
    """ 
        Streamlit components to run the app
    """

    st.title('Ticket Review App')

    with st.sidebar:

        st.checkbox(
            'Only non-reviewd tickets (not working yet)', value=True)

        st.write(
            """
            a) To read more about go to go/ticket-review-process
            b) You can find all reviewed tickets here XXXX
        """
        )


        headers = _get_websocket_headers()
        access_token = headers.get("X-Goog-Iap-Jwt-Assertion")
        user_id, user_email, error_str = validate_iap_jwt(access_token, "/projects/874764407517/global/backendServices/2612614375736935637")
        st.text_area("User", str(user_id)  + " | " + str(user_email) + " | " + str(error_str))
    
        #     Example access headers:
        # ticket_text = st.text_area('Headers', validate_iap_jwt(access_token, "/projects/874764407517/global/backendServices/2612614375736935637"))
        
    ticket_id = st.text_input(label="ticket_id", value='199393')

    t = st.button("Get ticket for review", type="primary")

    col1, col2 = st.columns(2)

    with col1.container(height=1000):

        # Button to trigger the query execution
        if t:

            df = get_ticket(ticket_id)

            subject = df["subject"].iloc[0]
            created_at = df["created_at"].iloc[0]
            lastupdate_at = df["lastupdate_at"].iloc[0]
            ticket_id = df["id"].iloc[0]
            ticket_prio = df["priority"].iloc[0]
            cloud= df["custom_platform"].iloc[0]
            product = df["custom_product"].loc[0]
            escalated = df["escalated"].iloc[0]

            st.markdown(    f"**{subject}**")
            with st.expander("Ticket Details 💡", expanded=True):
                st.markdown( f"opened at *{created_at}* and closed on *{lastupdate_at}* 🏁")

                tagger_component("", [ticket_prio, escalated, cloud, product],
                                    color_name=["grey", "red", "green", "green"])

            #with st.expander("AI generated Summary💡", expanded=False):
            #    st.write(
            #        """
            #            (comin soon)
            #        """
            #    )

            st.divider()

            for index in range(len(df)):
                comments = df["body"].iloc[index]
                st.write(f"{comments}")
                st.divider()

    with col2.container(height=1000):

        with st.form(key='review', border=False, clear_on_submit=True):

            with st.expander("Things to consider for a good ticket review 💡", expanded=False):
                st.write( # FIXME: write a meaningfull decription here
                    """
                    - What kind of information is in this database?
                    - What percentage of orders are returned?
                    - How is inventory distributed across our regional distribution centers?
                    - Do customers typically place more than one order?
                    - Which product categories have the highest profit margins?
                """
                )

            # Star rating
            reponse_rating = st.slider(
                'Quality of Responses: accuracy, clarity, and completeness', 1, 5,
                help="A score of 1 indicates poor quality, while a score of 5 indicates excellent quality.")
            time_rating = st.slider(
                'Timeliness of Responses: promptness of follow-ups, resolution time, and efficiency', 1, 5,
                help="A score of 1 indicates significant delays and 5 indicates consistently prompt and timely responses throughout the entire case interaction.")
            kindness_rating = st.slider(
                'Agent Kindness: friendliness, politeness, and empathy', 1, 5,
                help="A score of 1 indicates a lack of kindness and 5 indicates exceptional kindness.")
            complexity_rating = st.slider(
                'Complexity Handling', 1, 5,
                help="A score of 1 indicates poor handling (missing key details, inadequate solutions) and 5 indicates excellent handling (thorough analysis, effective resource use, clear communication).")
            knowledge_rating = st.slider(
                'CRE Knowledge and Expertise',  1, 5,
                help="A score of 1 indicates a lack of expertise and 5 indicates high expertise.")

            # Checkboxes for Knowledge assets
            cola, colb = st.columns(2)

            with cola:
                needs_cre_feedback = st.checkbox(
                    'Needs a cre-feedback', help="This is the tooltip for")
                good_story = st.checkbox('This is a good story')
            with colb:
                blogpost_candidate = st.checkbox(
                    'This is a blog-post candidate')
                playbook_candidate = st.checkbox(
                    'This is a playbook candidate')
                casestudy_candidate = st.checkbox(
                    'This is a case study candidate')

            tags = st.multiselect("Adherence to Company Values",
                                  ["#wow-the-customer", "#act-as-one-team", "#see-it-through",
                                      "#be-entrepreneurial", "#pursue-knowledge", "#have-fun"],
                                  [])  # pre-filled-values

            reviewer_thoughts = st.text_area(
                "Learning and Improvement Feedback(*)",  ' ', help="This is a mandatory field")

            submit_form = st.form_submit_button(
                    'Submit review 🏁', type="primary")
            #FIXME: grey it out, when no ticket was loaded

        if submit_form:

            #FIXME: only allow submit when a ticket was loaded
            # use session_state for that : https://discuss.streamlit.io/t/streamlit-button-disable-enable/31293
            # when the column is loaded add something to session state to indicate a ticket has been loaded

            if reviewer_thoughts and reponse_rating and time_rating:

                timestamp = datetime.datetime.now()

                data = {
                    'ticket': ticket_id,
                    'timestamp': timestamp,
                    'review': {

                        'reponse_rating': reponse_rating,
                        'time_rating': time_rating,
                        'kindness_rating': kindness_rating,
                        'complexity_rating': complexity_rating,
                        'knowledge_rating': knowledge_rating,

                        'blogpost_candidate': blogpost_candidate,
                        'playbook_candidate': playbook_candidate,
                        'casestudy_candidate': casestudy_candidate,

                        'reviewer_thoughts': reviewer_thoughts,

                        'needs_cre_feedback': needs_cre_feedback,
                        'good_story': good_story,

                        'tags': tags
                    }
                }

                db.collection('feedback').add(data) # autogenerates an docuemnt ID

                st.toast('Thanks for submitting a review!', icon='🎉')               

            else:
                st.warning("Please add a review before submitting")

if __name__ == "__main__":
    main()
