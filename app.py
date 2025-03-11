#import the necessary libraries
import streamlit as st
import pandas as pd
import plotly.express as px
from models import generate_response
from functions import authenticate_user, register_user, save_emotions_to_supabase, get_user_emotions

#set the cover image
st.image('portada.webp', use_container_width=True)

#set the title
st.title('🤖 :blue[EmotiBot]')
st.subheader(':blue[Therapeutic Chatbot with Emotion Analysis]')

#customize the appearance of the application
st.markdown(
    f"""
    <style>
        .stApp {{
            background-color: #0ee3bf; 
        }}
        .block-container {{
            max-width: 1200px;
            margin: auto;
        }}
        .chatbot-response {{
            background-color: #b3d9ff; 
            padding: 10px;
            margin-top: 10px;
            border-radius: 5px;
        }}
        div.stButton > button {{
            background-color: #0c99eb;
            color: white;
            border-radius: 5px;
            border: none;
            padding: 8px 16px;
            font-size: 16px;
        }}
        div.stButton > button:hover {{
            background-color: #075be0;
        }}
        textarea {{
            background-color: #b3d9ff !important;
            color: black !important;
        }}
    </style>
    """,
    unsafe_allow_html=True
)

#manage the session state in Streamlit using st.session_state.
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "show_bar_chart" not in st.session_state:
    st.session_state.show_bar_chart = False
if "show_line_chart" not in st.session_state:
    st.session_state.show_line_chart = False

#login or register
if not st.session_state.authenticated:
    tab_login, tab_register = st.tabs(["Login", "Register"])
    
    with tab_login:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Log in"):
            user_id = authenticate_user(username, password)
            if user_id is None:
                st.error("Invalid username or password")
            else:
                st.session_state.authenticated = True
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.success(f"Login successful, {username}!")
                st.rerun()
    
    with tab_register:
        st.subheader("Register")
        new_email = st.text_input("Email")
        new_password = st.text_input("New password", type="password")
        
        if st.button("Sign up"):
            user_id, result = register_user(new_email, new_password)
            if user_id:
                st.success(result)
            else:
                st.error(result)

#if the user is authenticated, display the chat interface and graphics
if st.session_state.authenticated:
    st.markdown(f"Welcome, {st.session_state.username}")

    #distribute the chat and graphics in two columns
    col1, col2 = st.columns([3, 3], gap="large")  

    with col1: 
        user_input = st.text_area("Tell me how you feel:", key="user_input")
        
        if st.button("Send Message"):
            if user_input.strip():
                response, detected_emotions = generate_response(user_input)
                st.session_state.last_response = response
                st.session_state.last_emotion = ", ".join([emotion[0] for emotion in detected_emotions])
                save_emotions_to_supabase(st.session_state.user_id, detected_emotions)
                st.rerun()

        if "last_response" in st.session_state:
            st.markdown(f'<div class="chatbot-response">{st.session_state.last_response}</div>', unsafe_allow_html=True)
            st.write(f"**Detected emotions:** {st.session_state.last_emotion}")

    with col2: 
        user_emotions = get_user_emotions(st.session_state.user_id)

        if user_emotions.empty:
            st.warning("No data available. Try sending a message first.")
        else:
            if st.button("Show Emotion Frequency"):
                st.session_state.show_bar_chart = True
                st.session_state.show_line_chart = False
                
            if st.button("Show Emotion Evolution"):
                st.session_state.show_line_chart = True
                st.session_state.show_bar_chart = False  

            emotion_colors = {
                "sadness": "#0761e8", 
                "fear": "#000000", 
                "joy": "#FFA500",  
                "surprise": "#8A2BE2",  
                "disgust": "#228B22",  
                "neutral": "#D3D3D3", 
                "anger": "#FF0000"  
            }

            #show bar chart if activated
            if st.session_state.show_bar_chart:
                emotion_counts = user_emotions["emotion"].explode().value_counts().reset_index()
                emotion_counts.columns = ["Emotion", "Frequency"]

                fig_bar = px.bar(
                    emotion_counts, 
                    x="Emotion", 
                    y="Frequency", 
                    color="Emotion",
                    color_discrete_map=emotion_colors  
                )

                fig_bar.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',  
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    title_text="",
                    xaxis=dict(showgrid=False, tickfont=dict(color="black"), title_text=""),  
                    yaxis=dict(showgrid=False, tickfont=dict(color="black"), title_text="")   
                )

                st.plotly_chart(fig_bar, use_container_width=True)

            #show line bar if activated
            if st.session_state.show_line_chart:
                emotion_timeline = user_emotions.explode("emotion")

                emotion_timeline["week"] = emotion_timeline["timestamp"].dt.to_period("W").astype(str)
                unique_weeks = sorted(emotion_timeline["week"].unique())
                week_labels = {week: f"Week {i+1}" for i, week in enumerate(unique_weeks)}
                emotion_timeline["week"] = emotion_timeline["week"].map(week_labels)
                emotion_weekly = emotion_timeline.groupby(["week", "emotion"]).size().reset_index(name="count")

                fig_line = px.line(
                    emotion_weekly, 
                    x="week", 
                    y="count", 
                    color="emotion",
                    markers=True,
                    color_discrete_map=emotion_colors  
                )

                fig_line.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',  
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=True,  
                    title_text="",
                    legend_title=dict(text="Emotion", font=dict(color="black")),
                    xaxis=dict(
                        showgrid=False, 
                        tickfont=dict(color="black"), 
                        title_text=""  
                    ),  
                    yaxis=dict(
                        showgrid=False, 
                        tickfont=dict(color="black"), 
                        title_text="" 
                    )   
                )

                st.plotly_chart(fig_line, use_container_width=True)
 