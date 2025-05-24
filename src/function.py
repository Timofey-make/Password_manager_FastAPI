import hashlib
import json
import random
import sqlite3
from functools import wraps
import base64
from flask import Flask, session, flash, redirect, url_for
import base64


# кодирование пароля
def encrypt(text):
    return base64.b64encode(text.encode()).decode()


# декодирование пароля
def decrypt(encrypted_text):
    return base64.b64decode(encrypted_text.encode()).decode()


# генератор паролей
def generator_password(length, myword):
    output = ''
    if len(myword) != 0:
        words = myword.split()
    else:
        with open('static/words.json', 'r', encoding='utf-8') as f:
            words = json.load(f)
    special_chars = ["&", "#", "%", "$", "@", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

    while len(output) < length:
        random_num = random.randint(1, 10)
        if random_num < 4:
            output += random.choice(words)
        else:
            output += random.choice(special_chars)

    return output[:length]


# проверка если в сессии пользователь
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:  # Проверяем session['user'] вместо session['user_id']
            flash('Пожалуйста, войдите в систему', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# хэширование пароля
def hash_password(password):
    """хэширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()
