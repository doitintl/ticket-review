import streamlit as st
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPICallError
from streamlit_extras.tags import tagger_component
from streamlit_star_rating import st_star_rating


# Configure BigQuery access (replace with your details)
credentials_path = ".creds/doit-ticket-review-ac07818e7b29.json"
client = bigquery.Client.from_service_account_json(credentials_path)
project_id = "doit-ticket-review"

user_query = "SELECT * FROM `doit-ticket-review.sample_data.v1` LIMIT 1"


def main():
    st.title('Ticket Review App')
    st.write("Help us revwing tickets!")

    st.divider()

    # Button to trigger the query execution
    if st.button("Get a random ticket for review"):

        # Execute the query on BigQuery
        try:
            query_job = client.query(user_query)
            results = query_job.result()  # Waits for the query to complete

            # Display the results as a Pandas dataframe
            df = results.to_dataframe()

            subject = df["subject"].iloc[0]
            created_at = df["created_at"].iloc[0]
            st.markdown(
                f"**{subject}** opened at *{created_at}* and closed on *May, 31st 2024* 🏁")

            tagger_component("", [df["priority"].iloc[0], df["custom_platform"].iloc[0], "escalated", df["status"].iloc[0]],
                             color_name=["grey", "grey", "red", "green"])

            comments = df["comment"].iloc[0]
            st.markdown(f"{comments}")

            # favorite_command = df.loc[df["id"].idxmax()]["subject"]
            # st.markdown(f"Your favorite ticket is **{favorite_command}** 🎈")

            st.divider()

            st.dataframe(
                df,
                # columns=['custom_product', 'summary'],
                hide_index=True,
                use_container_width=True)

            st.divider()

            # Text area for ticket input
            ticket_text = st.text_area(
                'Ticket Text', 'Enter the ticket text here...')

            # Text area for reviewer's thoughts
            reviewer_thoughts = st.text_area(
                'Your Thoughts', 'Enter your thoughts here...')

            # Star rating
            star_rating = st.slider('Star Rating', 1, 5)

            st_star_rating(label="", maxValue=5, defaultValue=3, key="rating")

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

        except GoogleAPICallError as e:
            st.error(f"API Error: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    st.sidebar.title("Sidebar options")
    main()
