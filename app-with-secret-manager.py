import boto3
from botocore.exceptions import ClientError
from flask import Flask, request, render_template
from flaskext.mysql import MySQL
import json

app = Flask(__name__)

# Function to retrieve secrets from AWS Secrets Manager
def get_secret():
    secret_name = "prod/App/Beta"  # Buraya kendi secret adını yaz
    region_name = "us-east-1"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    # Parse the secret string as JSON
    secret = json.loads(get_secret_value_response['SecretString'])
    return secret

# Retrieve AWS secrets and configure MySQL
secrets = get_secret()
app.config['MYSQL_DATABASE_HOST'] = secrets['host']
app.config['MYSQL_DATABASE_USER'] = secrets['username']
app.config['MYSQL_DATABASE_PASSWORD'] = secrets['password']
app.config['MYSQL_DATABASE_DB'] = secrets['dbname']
app.config['MYSQL_DATABASE_PORT'] = int(secrets['port'])  # str ise int'e çevir

mysql = MySQL()
mysql.init_app(app)

# Connect to database
connection = mysql.connect()
connection.autocommit(True)
cursor = connection.cursor()

# Create users table and insert data (1 kez çalıştırılmalı!)
drop_table = 'DROP TABLE IF EXISTS users;'
users_table = """
CREATE TABLE users (
  username VARCHAR(50) NOT NULL,
  email VARCHAR(50),
  PRIMARY KEY (username)
);
"""
data = """
INSERT INTO users 
VALUES 
    ("dora", "dora@amazon.com"),
    ("john", "john@google.com"),
    ("sencer", "sencer@bmw.com"),
    ("uras", "uras@mercedes.com"),
    ("ares", "ares@porche.com");
"""
cursor.execute(drop_table)
cursor.execute(users_table)
cursor.execute(data)

# Find emails by keyword
def find_emails(keyword):
    query = f"SELECT * FROM users WHERE username LIKE '%{keyword}%';"
    cursor.execute(query)
    result = cursor.fetchall()
    user_emails = [(row[0], row[1]) for row in result]
    if not user_emails:
        user_emails = [('Not found.', 'Not found.')]
    return user_emails

# Insert new email
def insert_email(name, email):
    if not name or not email:
        return 'Username or email can not be empty!!'

    query = f"SELECT * FROM users WHERE username = '{name}';"
    cursor.execute(query)
    result = cursor.fetchall()

    if not result:
        insert = f"INSERT INTO users VALUES ('{name}', '{email}');"
        cursor.execute(insert)
        return f'User {name} and {email} have been added successfully'
    else:
        return f'User {name} already exists.'

# Route to search emails
@app.route('/', methods=['GET', 'POST'])
def emails():
    if request.method == 'POST':
        user_name = request.form['user_keyword']
        user_emails = find_emails(user_name)
        return render_template('emails.html', name_emails=user_emails, keyword=user_name, show_result=True)
    else:
        return render_template('emails.html', show_result=False)

# Route to add new email
@app.route('/add', methods=['GET', 'POST'])
def add_email():
    if request.method == 'POST':
        user_name = request.form['username']
        user_email = request.form['useremail']
        result = insert_email(user_name, user_email)
        return render_template('add-email.html', result_html=result, show_result=True)
    else:
        return render_template('add-email.html', show_result=False)

# Run app
if __name__ == '__main__':
    app.run(debug=True)
    # app.run(host='0.0.0.0', port=80)  # Production için
