import datetime

import streamlit as st
import pandas as pd
import numpy as np
from google.api_core.exceptions import GoogleAPICallError
from google.auth.transport import requests
from google.cloud import bigquery, firestore, firestore_admin_v1
from google.oauth2 import id_token
from streamlit.web.server.websocket_headers import _get_websocket_headers
from streamlit_extras.tags import tagger_component
from streamlit_extras.bottom_container import bottom


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
    page_title="Ticket Review @ DoiT",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

#st.logo("https://help.doit.com/favicon-32x32.png")

PROJECT = "doit-ticket-review"

client = bigquery.Client()
client_fb = firestore_admin_v1.FirestoreAdminClient()
db = firestore.Client(project=PROJECT)

@st.cache_data(ttl=600)
def get_ticket(ticket_category):
    """ 
        Getting Ticket data from a BigQuery dataset. 
    """

    try:
        query = (f" SELECT *EXCEPT(comment) FROM `doit-ticket-review.sampled_data.sampled_tickets`, UNNEST(comment) AS c"
                 f" WHERE ticket_id = ("
                 f"     SELECT ANY_VALUE(ticket_id) FROM `doit-ticket-review.sampled_data.sampled_tickets` "
                 f"     WHERE custom_product = '{ticket_category}' LIMIT 1 )"
                 f" ORDER BY   comment_create_ts ASC ")
        query_job = client.query(query)
        results = query_job.result()  # Waits for the query to complete
        return results.to_dataframe()

        # FIXME: handle non-existent tickets gracefully

    except GoogleAPICallError as e:
        st.error(f"API Error: {e}")
        return e

def get_ticket_categories():
    """ 
    Getting a list of ticket categories
    """

    try:
        query = " SELECT custom_product FROM `doit-ticket-review.sampled_data.sampled_tickets` GROUP BY 1"
        query_job = client.query(query)
        results = query_job.result()  # Waits for the query to complete

        return results.to_dataframe()

    except GoogleAPICallError as e:
        st.error(f"API Error: {e}")
        return e

def user_details():
    """ 
        Getting all user detials from headers
    """

    headers = _get_websocket_headers()
    access_token = headers.get("X-Goog-Iap-Jwt-Assertion")
    user_id, user_email, error_str = validate_iap_jwt(access_token, "/projects/874764407517/global/backendServices/2612614375736935637")
    st.markdown(f"User {user_id} {user_email} {error_str}")

def main():
    """ 
        Streamlit components to run the app
    """

    st.title('Ticket Review App')

    with st.container(border=True):
        with st.status("Loading tickets...", expanded=True):
            ticket_category = st.selectbox('Select a ticket category', get_ticket_categories())

    col1, col2 = st.columns([0.6, 0.4])

    with col1.container(height=1000):

        df = get_ticket(ticket_category)

        if len(df) == 0:
            st.warning('No ticket avilible for review.', icon="⚠️")
            return

        subject = df["subject"].iloc[0]
        created_at = df["ticket_creation_ts"].iloc[0]
        lastupdate_at = pd.to_datetime(df['lastupdate_at'].iloc[0])
        resolution_time = lastupdate_at - created_at
        ticket_id = df["id"].iloc[0]
        ticket_prio = df["priority"].iloc[0]
        cloud= df["custom_platform"].iloc[0]
        product = df["custom_product"].loc[0]
        escalated = df["escalation"].iloc[0]
        csat = df["csat"].iloc[0]
        frt = df["frt"].iloc[0]

        st.markdown(f"**{subject}**")

        tagger_component("", [ticket_prio, escalated, cloud, product, f"🏁 time-to-solve: {resolution_time} 🏁", f"CSAT: {csat}", f"FRT: {frt}"],
                                color_name=["grey", "red", "orange", "green", "grey", "grey", "grey"])

        with st.expander("Ticket Statstics 💡", expanded=False):
            st.markdown( f"Opened at *{created_at}* and closed on *{lastupdate_at}*")

            chart_data = pd.DataFrame(df, columns=["comment_create_ts", "time_to_reply", "user_type","comments"])
            chart_data["color"] = np.random.choice(['#FC3165', "#303DA8"], len(df))
            #st.write(chart_data)

            st.scatter_chart(
                chart_data,
                x='comment_create_ts',
                y=["time_to_reply"],
                size='user_type',
                color='color'
            )

        #with st.expander("AI generated Summary💡", expanded=False):
        #    st.write(
        #        """
        #            (comin soon)
        #        """
        #    )

        for index in range(len(df)):
            comments = df["body"].iloc[index]
            st.write(f"{comments}")
            st.divider()
            #ttr = df["time_to_reply"].iloc[index]
            #st.write(f"{ttr}")
            #st.divider()


            #FIXME: Mark internal comments in another color
            #FIXME: Mark externa comments in another colour

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
                'Quality of Responses: accuracy, clarity, and completeness'
                , 0, 5,
                help="A score of 1 indicates poor quality, while a score of 5 indicates excellent quality.")
            time_rating = st.slider(
                'Timeliness of Responses: promptness of follow-ups, resolution time, and efficiency'
                , 0, 5,
                help="A score of 1 indicates significant delays and 5 indicates"
                    "consistently prompt and timely responses throughout the entire case interaction.")
            kindness_rating = st.slider(
                'Agent Kindness: friendliness, politeness, and empathy'
                , 0, 5,
                help="A score of 1 indicates a lack of kindness and 5 indicates exceptional kindness.")
            complexity_rating = st.slider(
                'Complexity Handling'
                , 0, 5,
                help="A score of 1 indicates poor handling (missing key details, inadequate solutions)"
                    "and 5 indicates excellent handling (thorough analysis, effective resource use, clear communication).")
            knowledge_rating = st.slider(
                'CRE Knowledge and Expertise'
                , 0 , 5,
                help="A score of 1 indicates a lack of expertise and 5 indicates high expertise.")

            # Checkboxes for Knowledge assets
            cola, colb = st.columns(2)

            with cola:
                blogpost_candidate = st.checkbox(
                    'This is a **blog-post** candidate')
                playbook_candidate = st.checkbox(
                    'This is a **playbook** candidate')
                casestudy_candidate = st.checkbox(
                    'This is a **case study** candidate')
            with colb:
                needs_cre_feedback = st.checkbox(
                    'Needs a cre-feedback', help="We have a seperate process for this")
                good_story = st.checkbox('This is a good story')

            tags = st.multiselect("Adherence to Company Values",
                                ["#wow-the-customer", "#act-as-one-team", "#see-it-through",
                                    "#be-entrepreneurial", "#pursue-knowledge", "#have-fun"],
                                [])  # pre-filled-values

            reviewer_thoughts = st.text_area(
                "Learning and Improvement Feedback(*)",  
                "It was the best of times, it was the worst of times, it was the age of "
                "wisdom, it was the age of foolishness, it was the epoch of belief, it "
                "was the epoch of incredulity, it was the season of Light, it was the "
                "season of Darkness, it was the spring of hope, it was the winter of "
                "despair, (...)",
                help="This is a mandatory field",
                height= 100)

            st.session_state.type = "primary"

            submit_form = st.form_submit_button(
                    'Submit review 🏁', type=st.session_state.type, use_container_width = True)
            #FIXME: grey it out, when no ticket was loaded

        if submit_form:

            #FIXME: only allow submit when a ticket was loaded
            # use session_state for that : https://discuss.streamlit.io/t/streamlit-button-disable-enable/31293
            # when the column is loaded add something to session state to indicate a ticket has been loaded

            if reviewer_thoughts and reponse_rating != 0 and time_rating:

                timestamp = datetime.datetime.now()

                data = {
                    'ticket': int(ticket_id),
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

                        'tags': tags,

                        'reviewer': "philipp@doit.com"
                    }
                    # FIXME: add reviewer name by looking at the Streamlit credentials
                }

                st.info(data)

                db.collection('feedback').add(data) # autogenerates an docuemnt ID

                st.toast('Thanks for submitting a review!', icon='🎉')       

            else:
                st.warning("Please add a review before submitting")

    with bottom():
        user_details()

if __name__ == "__main__":
    main()
