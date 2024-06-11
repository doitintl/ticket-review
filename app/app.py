import streamlit as st
from google.cloud import bigquery
from google.cloud import firestore
from google.cloud import firestore_admin_v1
from google.api_core.exceptions import GoogleAPICallError
from streamlit_extras.tags import tagger_component
import datetime

st.set_page_config(
    page_title="Ticket Review App",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

PROJECT = "doit-ticket-review"
CREDS_PATH = ".creds/doit-ticket-review-ac07818e7b29.json"

client = bigquery.Client.from_service_account_json(CREDS_PATH)
client_fb = firestore_admin_v1.FirestoreAdminClient()
db = firestore.Client(project="doit-ticket-review")

@st.cache_data
def get_ticket(id):
    try:
        query = 'SELECT *EXCEPT(comment), "2024-06-06 12:12.12" as  closed_at, "escalated" as escalation_status FROM `doit-ticket-review.sample_data.v1`, UNNEST(comment) as c WHERE id = 199393'
        query_job = client.query(query)
        results = query_job.result()  # Waits for the query to complete
        return results.to_dataframe()

    except GoogleAPICallError as e:
        st.error(f"API Error: {e}")

def main():

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

    ticket_id = st.text_input(
        label="ticket_id", value='199393')

    t = st.button("Get ticket for review", type="primary")

    col1, col2 = st.columns(2)

    with col1.container(height=800):

        # Button to trigger the query execution
        if t:

            df = get_ticket(ticket_id)

            subject = df["subject"].iloc[0]
            created_at = df["created_at"].iloc[0]
            closed_at = df["closed_at"].iloc[0]
            ticket_id = df["id"].iloc[0]

            st.markdown(    f"**{subject}**")
            with st.expander("Ticket Details 💡", expanded=True):
                st.markdown( f"opened at *{created_at}* and closed on *{closed_at}* 🏁")

                tagger_component("", [df["priority"].iloc[0],
                                        df["custom_platform"].iloc[0],
                                        df["escalation_status"].iloc[0],
                                        {ticket_id}],
                                    color_name=["grey", "grey", "red", "green"])

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

    with col2.container(height=800):

        with st.form(key='review', border=False, clear_on_submit=True):

            with st.expander("Things to consider for a good ticket review 💡", expanded=False):
                st.write(
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

            # FIXME: allow submit only when ticket has been loaded - otherwise grey out??!

        

        if submit_form:

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

                st.toast('Thanks for helping us!', icon='🎉')

            else:
                st.warning("Please add a review before submitting")


if __name__ == "__main__":
    main()
