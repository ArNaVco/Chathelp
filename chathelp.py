from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
import random
import os
import time

app = Flask(__name__)

# Database setup
def init_db():
    with sqlite3.connect('emotional_support.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                mood TEXT,
                interaction_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS mood_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mood TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                keyword TEXT,
                response_text TEXT NOT NULL
            )
        ''')
        c.execute('SELECT COUNT(*) FROM responses')
        if c.fetchone()[0] == 0:
            default_responses = [
                ('keyword', 'sad', 'I hear that you\'re feeling down. 💙 It\'s okay to feel this way. Would you like to talk about what\'s on your mind?'),
                ('keyword', 'happy', 'It\'s wonderful that you\'re feeling happy! 😊 What\'s contributing to your joy today?'),
                ('mood', 'positive', 'That\'s wonderful to hear! 😊 What\'s bringing you joy today?'),
                ('mood', 'neutral', 'Thanks for sharing. 🌼 How can I support you today?'),
                ('mood', 'negative', 'I\'m sorry you\'re feeling this way. 💙 Remember, you\'re not alone in this.'),
                ('game', None, 'Let\'s play a quick game! I\'m thinking of a number between 1 and 10. Can you guess it?'),
                ('joke', None, 'Why don\'t scientists trust atoms? Because they make up everything! 😄'),
                ('chat', None, 'Tell me about your favorite book or movie. What do you love about it?')
            ]
            c.executemany('INSERT INTO responses (category, keyword, response_text) VALUES (?, ?, ?)', default_responses)
        conn.commit()

init_db()

# Chatbot functionality
class EmotionalSupportChatbot:
    def __init__(self):
        self.user_mood = "neutral"
        self.cached_responses = self.load_responses()

    def load_responses(self):
        """Cache responses from the database to reduce queries."""
        with sqlite3.connect('emotional_support.db') as conn:
            c = conn.cursor()
            c.execute('SELECT category, keyword, response_text FROM responses')
            responses = c.fetchall()
        response_dict = {}
        for category, keyword, response_text in responses:
            key = (category, keyword)
            if key not in response_dict:
                response_dict[key] = []
            response_dict[key].append(response_text)
        return response_dict

    def get_response(self, category, keyword=None):
        """Fetch a random response from the cached responses."""
        key = (category, keyword)
        if key in self.cached_responses:
            return random.choice(self.cached_responses[key])
        return None

    def save_message(self, sender, content, mood, interaction_type="chat"):
        """Save a message to the database."""
        with sqlite3.connect('emotional_support.db') as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO chat_history (sender, content, mood, interaction_type)
                VALUES (?, ?, ?, ?)
            ''', (sender, content, mood, interaction_type))
            conn.commit()

    def get_bot_response(self, user_input):
        """Generate a bot response based on user input."""
        user_input = user_input.lower()
        if "game" in user_input:
            return self.get_response('game')
        elif "joke" in user_input:
            return self.get_response('joke')
        elif any(keyword in user_input for keyword in ['sad', 'happy', 'angry']):
            for keyword in ['sad', 'happy', 'angry']:
                if keyword in user_input:
                    return self.get_response('keyword', keyword)
        return self.get_response('chat') or "I'm here to listen. How can I help?"

chatbot = EmotionalSupportChatbot()

# Web routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    user_message = request.form['message']
    mood = request.form.get('mood', 'neutral')
    chatbot.save_message("User", user_message, mood)
    bot_response = chatbot.get_bot_response(user_message)
    chatbot.save_message("Sophia", bot_response, mood)
    return jsonify({'response': bot_response, 'mood': mood})

@app.route('/get_history', methods=['GET'])
def get_history():
    with sqlite3.connect('emotional_support.db') as conn:
        c = conn.cursor()
        c.execute('SELECT sender, content, timestamp FROM chat_history ORDER BY timestamp')
        messages = [{'sender': row[0], 'content': row[1], 'timestamp': row[2]} for row in c.fetchall()]
    return jsonify(messages)

if __name__ == '__main__':
    app.run(debug=True)