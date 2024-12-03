# -*- coding: utf-8 -*-
"""app_1.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1lZXhrDQKHv83S7o8PeqLuWSR7gTMr312
"""

# pip install transformers, streamlit, tensorflow, sentence_transformers

import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO
from textblob import TextBlob
from PIL import Image

import nltk, re
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize.toktok import ToktokTokenizer
tokenizer = ToktokTokenizer()
from nltk import word_tokenize
nltk.download('punkt', force=True)
#nltk.download('punkt_tab')
nltk.download('stopwords')
nltk.download('wordnet')

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Streamlit app
def main():
    st.title("SurveySage")

    st.sidebar.header("SurveySage")
    # Display the logo
    logo_path = "/Users/daviesha/Desktop/DATA 5420/Homework/Final/Streamlit_App/icon.png"
    logo = Image.open(logo_path)
    st.sidebar.image(logo, use_container_width = True)

    st.sidebar.header("Upload Your CSV File")
    uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])

    if uploaded_file is not None:
        # Read CSV
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            return

        st.subheader("Uploaded CSV")
        st.write(df.head())

        # Perform Cleaning
        st.subheader("Cleaned CSV")

        ### Clean CSV ###
        # steps to remove unnecessary rows and columns, reset index, and assign better column names

        def clean_csv(df):
            # remove unnecessary survey info columns
            df = df.drop(columns=['StartDate', 'EndDate', 'Status', 'IPAddress', 'Progress', 'Duration (in seconds)', 'Finished', 'ResponseId', 'RecipientLastName', 'RecipientFirstName', 'RecipientEmail', 'ExternalReference', 'LocationLatitude', 'LocationLongitude', 'DistributionChannel', 'UserLanguage'])
            # remove unnecessary rows (NAs, NaNs, survey labels, etc.)
            df = df.dropna(subset=df.columns[[1, 2, 3, 4]], how='all') # drops row if first 4 columns are all null
            df = df[~df['RecordedDate'].str.contains('ImportId', case=False)] # drops row if contains "ImportId" (survey labels)
            # Replace column namese with first row
            df.columns = df.iloc[0] # set first row as header
            df = df.drop(df.index[0]) # drops first row
            # reset index to start from 0
            df = df.reset_index(drop = True)

            # rename columns: !!!!!will need to edit if changes are made to survey!!!!!!
            # 'new column name' if 'word' contained in old column name
            df.columns = ['A_Number' if 'A-Number' in col else
                            'Date' if 'Date' in col else
                            'Suggestions' if 'suggestions' in col else
                            'Fav_Session' if 'session' in col else
                            'Team_Connection' if 'peer mentor' in col else
                            'Group_Inv' if 'join' in col else
                            'Huntsman_Sentiment' if 'describe the Huntsman' in col else
                            'Creative_Scale' if 'Creative' in col else
                            'Curious_Scale' if 'Curious' in col else
                            'Courageous_Scale' if 'Courageous' in col else
                            'Collaborative_Scale' if 'Collaborative' in col else
                            'College_Ready' if 'college will require' in col else
                            'Make_Friends' if 'can make friends' in col else
                            'Career_Success' if 'college will prepare me' in col else
                            'Business_Person' if 'person of business' in col else
                            'Excitement' if 'thrilled' in col else
                            'Course_Experience' if 'Describe your experience' in col else
                            col for col in df.columns]
            return(df)

        # apply main cleaning function to main csv file
        df = clean_csv(df)

        def clean_a_numbers(df):
            # Make all uppercase
            df['A_Number'] = df['A_Number'].str.upper()

            # Convert the column to string and handle NaN values
            df['A_Number'] = df['A_Number'].astype(str)

            # Use lambda to check if the value starts with 'A', and if not, prepend 'A'
            df['A_Number'] = df['A_Number'].apply(lambda x: 'A' + x if pd.notna(x) and not x.startswith('A') else x)

            # convert email addresses to just A Number
            df['A_Number'] = df['A_Number'].str.split('@', expand=True)[0]

            return(df)

        # apply A# cleaning to main csv file
        df = clean_a_numbers(df)

        ### Text Preprocessing ###
        # Make a copy of dataframe for edits
        df_edit = df.copy()

        # Add in custom Stop words
        stop_words = nltk.corpus.stopwords.words('english')
        stop_words = stop_words + ['freshmen', 'freshman', 'academy', 'school', 'course', 'class', 'program', 'huntsman', 'business']

        # remove "not" from stop word list because important for analysis
        if 'not' in stop_words:
          stop_words.remove('not')

        # Preprocessing Columns (Suggestions, Fav_Session, Team_Connection, Huntsman_Sentiment, Course_Experience)
          # Sentiment Analysis = Course_Experience, Team_Connection
          # Topic Modeling = Suggestions, Fav_Session, Huntsman Sentiment

        # Text Similarity Preprocessing
        def preprocess_text_tm(text):
            if not isinstance(text, str):
              return ""
            text = re.sub(r"[^a-zA-Z0-9]", " ", text.lower()) #removing everything except for letters & numbers
            tokens = nltk.word_tokenize(text)
            tokens = [token for token in tokens if token not in stop_words]
            lemmatizer = WordNetLemmatizer()
            tokens = [lemmatizer.lemmatize(token) for token in tokens]
            text = ' '.join(tokens)
            return text

        # Apply preprocessing to columns
        df_edit['Suggestions_clean'] = df_edit['Suggestions'].apply(preprocess_text_tm)
        df_edit['Fav_Session_clean'] = df_edit['Fav_Session'].apply(preprocess_text_tm)
        #df_edit['Huntsman_Sentiment_clean'] = df_edit['Huntsman_Sentiment'].apply(preprocess_text_tm)

        ### Text Similarity ###
        # categories for suggestions (name = description/keywords)
        sug_categories = {
            "None": "no, suggestions, nothing, none, nah, thought great, all good, amazing, really enjoyed, best, fun",
            "Make Class Optional": "make optional, not/do not require",
            "Class Time/Day": "change time of day when we meet, start end on time, wake up, earlier or later, morning afternoon evening, monday, tuesday, wednesday, thursday, friday",
            "Change Course Delivery": "less lecture, more interactive, engaging, fun, involve, activity, make shorter/longer",
            "Change Course Content": "talk, hear, learn more about different degrees, topics, skills, ideas, repetitive, speakers, focus on",
            "Meaningful Assignments": "more meaningful/beneficial assignments",
            "Changing Grading Weights": "give more points to assignments, attendance, attendance heavy",
            "Course Location": "location, stay, spot, visit places, inside outside, visit buildings, building",
            "More Relationship Building": "unity, group, team, peer, coach, get to know, together, small group, interact, mingle",
            "Change Name/Logo": "name, logo, dislike t-shirt/tee shirt",
            "Better Communication": "lost, confused, canvas, communication, texts, emails, info, information distribution",
            "More extra credit": "make up, extra credit, points back"
        }

        # categories for sessions (name = description/keywords)
        session_categories = {
            "Happiness": "happy, happiness",
            "Innovative Learning": "innovate, innovative, entrepreneurship, entrepreneur, invent, invention, household items",
            "Huntsman Culture": "culture, scotsman, steve young, walk through tunnel of staff, swag",
            "Majors & Mindsets": "degree, degrees, majors, accounting, finance, economics, marketing, different, professors, departments, faculty",
            "Authenticity": "authenticity, authentic, act, acting, actor, improv, improve, role play, comfort zone, theater, drama, spontaneous",
            "Data & Life": "data, data analytics, survey, app, sharad, carly",
            "Winning Mindset": "win, mindset, coach, volleyball, soccer",
            "Kickoff": "food, kickoff, kick off, tour",
            "Empathy": "empathy, feelings, covey",
            "Service": "service",
            "Dare Mighty Things": "dare, mighty, things, panel, generations",
            "Purpose": "purpose, find my purpose",
            "Identity & Belonging": "vulnerability, identity, belonging"
        }

        model = SentenceTransformer('all-MiniLM-L6-v2')

        def categorize_responses(df, response_column, category_col, categories, model = model, threshold = 0.15, ifna = 'None'):
            df[category_col] = "Other"
            responses = df[response_column]

            # vectorize responses and categories
            category_names = list(categories.keys())
            category_descriptions = list(categories.values())

            category_embeddings = model.encode(category_descriptions)

            # if response is blank then assign to "None Category"
            for i, response in enumerate(responses):
              if pd.isna(response) or response.strip() == "":
                df.loc[i, category_col] = ifna
                continue

              response_embedding = model.encode([response])
              similarities = cosine_similarity(response_embedding, category_embeddings).flatten()

              # if cosine similarity is > threshold then highest category
              max_similarity = max(similarities)
              if max_similarity >= threshold:
                best_category_idx = similarities.argmax()
                df.loc[i, category_col] = category_names[best_category_idx]

            return df

        df_edit = categorize_responses(df_edit, 'Suggestions_clean', 'suggestions_categories', sug_categories, model = model, threshold = 0.15, ifna = 'None')
        df_edit = categorize_responses(df_edit, 'Fav_Session_clean', 'session_categories', session_categories, model = model, threshold = 0.15, ifna = 'Unknown')

        ### Final Edits to csv ###
        # drop columns
        columns_to_drop = ['Suggestions_clean', 'Fav_Session_clean']
        df_edit = df_edit.drop(columns=[col for col in columns_to_drop if col in df_edit.columns])

        # Rearrange columns
        cols_arrange = ['Suggestions', 'suggestions_categories', 'Fav_Session', 'session_categories']
        df_sub = df_edit[cols_arrange]
        df_edit = df_edit.drop(columns=[col for col in cols_arrange if col in df_edit.columns])
        df_edit = pd.concat([df_edit, df_sub], axis=1)

        st.write(df_edit.head())

        # Download Main Cleaned CSV
        st.download_button(
            label="Download Cleaned CSV",
            data=convert_df_to_csv(df_edit),
            file_name="cleaned_data.csv",
            mime="text/csv"
        )

        st.subheader("Student Involvement CSV")

        ### Create Student Involvement CSV ###
        # Create columns based on Group_Inv column values and create lists of A-numbers per category
        # returns a csv of student involvement info
        def create_inv_csv(df):
            df = pd.DataFrame(df[['A_Number','Group_Inv']])

            # Break up Group_Inv column into individual words
            # Use apply() to replace NaN with an empty list
            df['Group_Inv'] = df['Group_Inv'].apply(lambda x: x.split(',') if isinstance(x, str) else [])

            # Get the unique values from the Group_Inv column
            unique_values = df['Group_Inv'].explode().unique()

            # Create a dictionary with empty lists for each unique value
            group_dict = {value: [] for value in unique_values}

            # Iterate over the DataFrame and add A_Number to the respective lists
            for index, row in df.iterrows():
              for group in row['Group_Inv']:
                group_dict[group].append(row['A_Number'])

            ## Convert dictionary of lists into a csv
            # Find the length of the longest list
            max_length = max(len(lst) for lst in group_dict.values())

            # Pad the shorter lists with NaN to match the length of the longest list
            for key in group_dict:
                group_dict[key] = group_dict[key] + [np.nan] * (max_length - len(group_dict[key]))

            # Convert the padded dictionary to a DataFrame
            student_inv = pd.DataFrame(group_dict)

            # return Dataframe
            return(student_inv)

        # create student inv dataframe
        student_inv = create_inv_csv(df)

        st.write(student_inv.head())

        # Download Student Involvement CSV
        st.download_button(
            label="Download Student Involvement CSV",
            data=convert_df_to_csv(student_inv),
            file_name="student_inv.csv",
            mime="text/csv"
        )

# Convert DataFrame to CSV for download
def convert_df_to_csv(df):
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    return buffer.getvalue()

# Run the app
if __name__ == "__main__":
    main()