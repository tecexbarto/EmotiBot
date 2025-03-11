#import the necessary libraries
import torch
from torch.nn.functional import softmax
import re
from transformers import RobertaTokenizer, RobertaForSequenceClassification, BartForConditionalGeneration, BartTokenizer

#load the emotion model
EMOTION_MODEL_NAME = "j-hartmann/emotion-english-distilroberta-base"
roberta_tokenizer = RobertaTokenizer.from_pretrained(EMOTION_MODEL_NAME)
roberta_model = RobertaForSequenceClassification.from_pretrained(EMOTION_MODEL_NAME)

#load the finetuned model
MODEL_PATH = "Bartix84/bart_large_finetuned"
bart_tokenizer = BartTokenizer.from_pretrained(MODEL_PATH, cache_dir="/home/user/app/cache", token=True)
bart_model = BartForConditionalGeneration.from_pretrained(MODEL_PATH, cache_dir="/home/user/app/cache", token=True)

#detect if a GPU is available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
roberta_model.to(device)
bart_model.to(device)

#list of emotions
emotion_labels = ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]

#create a function that analyzes the user's text and returns the emotions detected with a probability greater than a threshold
def detect_emotions(user_text, threshold=0.3):
    inputs = roberta_tokenizer(user_text, return_tensors="pt", truncation=True, padding=True).to(device)
    with torch.no_grad():
        outputs = roberta_model(**inputs)
    scores = softmax(outputs.logits, dim=1)
    
    detected_emotions = [(emotion_labels[i], scores[0][i].item()) for i in range(len(emotion_labels)) if scores[0][i].item() > threshold]
    
    return detected_emotions if detected_emotions else [("neutral", scores[0][4].item())]

#created a function that removes unwanted URLs, names of therapists, mentions of books and other unwanted things
def clean_generated_text(model_text):
    model_text = re.sub(r"\b(www\.[A-Za-z0-9.-]+|https?://\S+)", "", model_text)
    model_text = re.sub(r"\b(Mark MorrisLCSW|LivingYes\.org|Robin J. Landwehr)\b", "", model_text, flags=re.IGNORECASE)
    model_text = re.sub(r"\b(DBH|LPC|NCC|PhD|MD|LCSW)\b", "", model_text)
    model_text = re.sub(r"\b(I recommend reading|You should read|Look up .* on Amazon|Read .* by )\b.*", "", model_text, flags=re.IGNORECASE)

    phrases_to_remove = ["LIVING YES, A HANDBOOK FOR BEING HUMAN", "Amazon.com", "self-help book", "this book changed my life", "a must-read for anyone", "this book was very helpful"]

    for phrase in phrases_to_remove:
        model_text = model_text.replace(phrase, "")

    model_text = re.sub(r"\s+", " ", model_text).strip()

    return model_text

#this function generates a response based on the user's text
def generate_response(user_input):
    strongest_emotion = detect_emotions(user_input)[0][0]
    bart_input = f"The user feels {strongest_emotion} and has shared: '{user_input}'. Reply in a single paragraph with supportive words."
    
    inputs = bart_tokenizer(bart_input, return_tensors="pt", truncation=True, padding=True, max_length=512).to(device)
    
    output_ids = bart_model.generate(
        **inputs, 
        max_new_tokens=400,  
        min_new_tokens=50,  
        do_sample=True,  
        top_p=0.85,  
        temperature=0.8,  
        repetition_penalty=1.7,  
        early_stopping=True
    )

    response = bart_tokenizer.decode(output_ids[0], skip_special_tokens=True)
    response = clean_generated_text(response)

    return response, detect_emotions(user_input)

