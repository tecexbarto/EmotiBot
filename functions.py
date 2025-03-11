#import the necessary libraries
import os
import supabase
import bcrypt  
from dotenv import load_dotenv
import datetime
import pandas as pd

#configure the Supabase connection
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

#connect to Supabase
supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

#this function registers new users
def register_user(email, password):

    try:
        response = supabase_client.auth.sign_up({"email": email, "password": password})
        if response and hasattr(response, "user") and response.user:
            user_id = response.user.id  
            hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            user_data = {"id": user_id, "username": email, "password": hashed_password}
            db_response = supabase_client.table("users").insert(user_data).execute()

            if db_response.data: 
                print("✅ User successfully saved in the 'users' table.")
                return user_id, "User registered successfully!"
            else:
                print(f"⚠️ Error saving user in 'users': {db_response.error}")
                return None, "Error saving user in database."
        return None, "Error registering user."

    except Exception as e:
        print(f"❌ Exception in user registration: {str(e)}")
        return None, str(e)

#This function allows an existing user to log in
def authenticate_user(email, password):

    try:
        response = supabase_client.table("users").select("id, password").eq("username", email).execute()

        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            stored_password = user_data["password"]

            if stored_password.startswith("$2b$"):
                if bcrypt.checkpw(password.encode("utf-8"), stored_password.encode("utf-8")):
                    print("✅ Successful login with encrypted password")
                    return user_data["id"]
            else:
                if stored_password == password:
                    new_hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                    supabase_client.table("users").update({"password": new_hashed_password}).eq("id", user_data["id"]).execute()
                    print("🔄 Password encrypted and updated in the DB")
                    return user_data["id"]
                else:
                    print("❌ Incorrect password for user with plain text password")
                    return None
            print("❌ Incorrect password")
            return None

        print("❌ User not found")
        return None

    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

#save emotions in the Supabase database
def save_emotions_to_supabase(user_id, emotions):

    if not user_id:
        print("❌ Error: invalid user_id. No emotions will be saved.")
        return

    try:
        timestamp = datetime.datetime.now().isoformat()
        emotions_list = [emotion[0] for emotion in emotions] if emotions else ["neutral"]

        emotions_array = "{" + ",".join(f'"{emotion}"' for emotion in emotions_list) + "}"  

        data = {"user_id": user_id, "timestamp": timestamp, "emotion": emotions_array}

        response = supabase_client.table("emotions").insert(data).execute()
        
        if response.data: 
            print("✅ Emotions saved correctly in Supabase.")
        else:
            print(f"⚠️ Error saving emotions: {response.error}")
    
    except Exception as e:
        print(f"❌ Exception saving emotions: {str(e)}")

#this function retrieves the stored emotions of a user in Supabase and converts them into a Pandas dataframe
def get_user_emotions(user_id):
   
    response = supabase_client.table("emotions").select("*").eq("user_id", user_id).execute()
    emotions = response.data if response.data else []

    df = pd.DataFrame(emotions)
    
    if "timestamp" in df.columns and "emotion" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
        df["emotion"] = df["emotion"].apply(lambda x: eval(x) if isinstance(x, str) else x)

    return df
