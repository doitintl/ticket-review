import streamlit as st

def main():
    st.title('Ticket Review App')

    # Text area for ticket input
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