import streamlit as st
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPICallError
from streamlit_extras.tags import tagger_component
import requests
import time

st.set_page_config(
    page_title="Ticket Review App",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    #menu_items={
    #    'Get Help': 'https://www.extremelycoolapp.com/help',
    #    'Report a bug': "https://www.extremelycoolapp.com/bug",
    #    'About': "# This is a header. This is an *extremely* cool app!"
    #}
)



credentials_path = ".creds/doit-ticket-review-ac07818e7b29.json"
client = bigquery.Client.from_service_account_json(credentials_path)
PROJECT = "doit-ticket-review"


def req(json):

    r = requests.post('http://localhost:8501/',
                      data=json,
                      headers={'Content-Type': "m.content_type"},
                      timeout=8000)

    return r

@st.cache_data
def get_ticket(user_query):
    try:
            query_job = client.query(user_query)
            results = query_job.result()  # Waits for the query to complete
            return results.to_dataframe()

    except GoogleAPICallError as e:
        st.error(f"API Error: {e}")

def main():    

    st.title('Ticket Review App')

    with st.sidebar:

        review = st.checkbox('Only non-reviewd tickets', value=True)    

        t = st.button("Get a random ticket for review")
        
        st.write(
        """
            a) To read more about go to go/ticket-review-process
            b) You can find all reviewed tickets here XXXX
        """
        )
    


    query = st.text_input(label="query", value='SELECT *EXCEPT(comment)  FROM `doit-ticket-review.sample_data.v1`, UNNEST(comment) as c WHERE id = 199393')



    col1, col2 = st.columns(2)

    with col1.container(height=800):

        # Button to trigger the query execution
        if t:

            # Execute the query on BigQuery
          
                df = get_ticket(query)

                subject = df["subject"].iloc[0]
                created_at = df["created_at"].iloc[0]
                st.markdown(
                    f"**{subject}** opened at *{created_at}* and closed on *May, 31st 2024* 🏁")

                tagger_component("", [df["priority"].iloc[0],
                                    df["custom_platform"].iloc[0],
                                    "escalated", 
                                    df["status"].iloc[0]],
                                color_name=["grey", "grey", "red", "green"])

                st.divider()


                for index in range(len(df)):
                    comments = df["body"].iloc[index]
                    st.write(f"{comments}")
                    st.divider()


                # favorite_command = df.loc[df["id"].idxmax()]["subject"]
                # st.markdown(f"Your favorite ticket is **{favorite_command}** 🎈")


                #st.dataframe(
                #    df["body"],
                #    #"created_at", "user_id",
                #    # columns=['custom_product', 'summary'],
                #    hide_index=True,
                #    use_container_width=True)


                
    with col2.container(height=800):

        with st.form(key='review', border=False, clear_on_submit=True):
            # Text area for reviewer's thoughts

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

            reviewer_thoughts = st.text_area(
                'Your Thoughts', '')

            # Star rating
            star_rating = st.slider('Star Rating', 1, 5)
            # st_star_rating(label="", maxValue=5, defaultValue=3, key="rating")

            # Checkboxes
            good_story = st.checkbox('This is a good story')
            needs_cre_feedback = st.checkbox('Needs a cre-feedback')

            options = st.multiselect("multi-select",
                            ["#wow-the-customer", "#act-as-one-team", "#see-it-through"],
                            []) #pre-filled-values

            submit_form = st.form_submit_button('Submit review 🏁', type="primary")


        if submit_form:
            #st.write(submit_form)

            if reviewer_thoughts: # and star_rating:
            # add_user_info(id, name, age, email, phone, gender)
                json = reviewer_thoughts # + star_rating + needs_cre_feedback
                req(json)
                st.toast('Thanks for helping us!', icon='🎉')

                st.success(
                    f"ID:  XXXXX  \n Your Thoughts: {reviewer_thoughts}  \n Ratings: {star_rating}  \n needs_cre_feedback: {needs_cre_feedback}  \n Is good story?: {good_story}  \n Other: {options}"
                    )
            else:
                st.warning("Please add a review before submitting")

if __name__ == "__main__":
    #st.sidebar.title("Sidebar options")
    main()
