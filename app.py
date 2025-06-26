# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
import time
from datetime import datetime
import json
import secrets
import random
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def modify_riddles_table():
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Create a new table for riddle variants
    c.execute('''
        CREATE TABLE IF NOT EXISTS riddle_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            riddle_id INTEGER NOT NULL,
            question_variant TEXT NOT NULL,
            FOREIGN KEY (riddle_id) REFERENCES riddles (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Added riddle_variants table for multiple question variants")

# Run this once to add the new table
modify_riddles_table()

def add_user_question_variants_table():
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Create a table to track which variant is assigned to each user
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_question_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    riddle_id INTEGER NOT NULL,
    question_variant TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (riddle_id) REFERENCES riddles(id)
);
    ''')
    
    conn.commit()
    conn.close()
    print("Added user_question_variants table to track user's assigned questions")

# Run this once to set up the variant tracking
add_user_question_variants_table()

def init_db():
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Check if the column exists, if not add it
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    
    if "test_completed" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN test_completed INTEGER DEFAULT 0;")
        conn.commit()
        print("Added 'test_completed' column to users table.")
    
    conn.close()
    return "Database updated with test_completed column"

def add_image_column():
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()

    # Check if the "image" column already exists
    c.execute("PRAGMA table_info(riddles);")
    columns = [column[1] for column in c.fetchall()]
    
    if "image" not in columns:
        c.execute("ALTER TABLE riddles ADD COLUMN image TEXT;")  # Add missing column
        conn.commit()
        print("Added 'image' column to riddles table.")

    conn.close()

# Run this once to update the database schema
add_image_column()
init_db()

# Database initialization
def init_db():
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    # Riddles table
    # c.execute('''
    #     CREATE TABLE IF NOT EXISTS riddles (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         question TEXT NOT NULL,
    #         answer TEXT NOT NULL,
    #         hint1 TEXT NOT NULL,
    #         hint2 TEXT NOT NULL,
    #         hint3 TEXT NOT NULL
    #     )
    # ''')


    # Modify riddles table to include an image field
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS riddles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            hint1 TEXT NOT NULL,
            hint2 TEXT NOT NULL,
            hint3 TEXT NOT NULL,
            image TEXT  -- New column for storing image filenames
        )
    ''')

    
    # User progress table
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            riddle_id INTEGER NOT NULL,
            score INTEGER DEFAULT 10,
            completed INTEGER DEFAULT 0,
            hint1_used INTEGER DEFAULT 0,
            hint2_used INTEGER DEFAULT 0,
            hint3_used INTEGER DEFAULT 0,
            answer_attempt TEXT,
            completion_time TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (riddle_id) REFERENCES riddles (id),
            UNIQUE(user_id, riddle_id)
        )
    ''')
    
    # Check if admin user exists
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    admin_user = c.fetchone()

    if admin_user:
        # Update password if the admin user exists
        c.execute("UPDATE users SET password = ? WHERE username = 'admin'", ('adtechevent',))
    else:
        # Insert new admin user if not exists
        c.execute("INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
                ('admin', 'admin@example.com', 'adtechevent', 1))

    conn.commit()  # Ensure changes are saved
    
    # Insert sample riddles if none exist
    c.execute("SELECT COUNT(*) FROM riddles")
    if c.fetchone()[0] == 0:
        sample_riddles = [
            (
                "I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?",
                "echo",
                "I repeat what I hear.",
                "You might find me in mountains and canyons.",
                "I am a returning sound."
            ),
            (
                "The more you take, the more you leave behind. What am I?",
                "footsteps",
                "I'm related to walking.",
                "I'm marks left behind.",
                "You make these when you walk on sand or snow."
            ),
            (
                "What has keys but no locks, space but no room, and you can enter but not go in?",
                "keyboard",
                "I'm used for typing.",
                "I have many buttons.",
                "You use me with a computer."
            ),
            (
                "What is always in front of you but can't be seen?",
                "future",
                "It's related to time.",
                "It hasn't happened yet.",
                "It's what's coming next in your life."
            ),
            (
                "I have cities, but no houses. I have mountains, but no trees. I have water, but no fish. What am I?",
                "map",
                "I represent real places.",
                "I'm used for navigation.",
                "I show you where things are located."
            )
        ]
        
        c.executemany("INSERT INTO riddles (question, answer, hint1, hint2, hint3) VALUES (?, ?, ?, ?, ?)", sample_riddles)
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('riddle_test.db')
        c = conn.cursor()
        
        try:
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                     (username, email, password))
            
            # Get the user id
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            user_id = c.fetchone()[0]
            
            # Initialize user progress for all riddles
            c.execute("SELECT id FROM riddles")
            riddle_ids = c.fetchall()
            
            for riddle_id in riddle_ids:
                c.execute("INSERT INTO user_progress (user_id, riddle_id) VALUES (?, ?)",
                         (user_id, riddle_id[0]))
                
            conn.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose a different one.')
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('riddle_test.db')
        c = conn.cursor()
        
        c.execute("SELECT id, username, is_admin FROM users WHERE username = ? AND password = ?",
                 (username, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_admin'] = user[2]
            
            if user[2]:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('test'))
        else:
            flash('Invalid username or password.')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def has_completed_test(user_id):
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()

    # Check if the test has been completed
    c.execute("SELECT test_completed FROM users WHERE id = ?", (user_id,))
    test_completed = c.fetchone()

    conn.close()

    return test_completed and test_completed[0] == 1  # Returns True if test_completed is 1


@app.route('/test')
def test():
    if 'user_id' not in session:
        flash('Please log in to take the test.')
        return redirect(url_for('login'))
    
    if has_completed_test(session['user_id']):
        flash('You have already completed this test.')
        return redirect(url_for('results'))
    
    return redirect(url_for('test_without_images'))

@app.route('/test_without_images')
def test_without_images():
    if 'user_id' not in session:
        flash('Please log in to take the test.')
        return redirect(url_for('login'))

    conn = sqlite3.connect('riddle_test.db')
    conn.row_factory = sqlite3.Row  
    c = conn.cursor()
    if has_completed_test(session['user_id']):
        flash('You have already completed this test. You cannot take it again.')
        return redirect(url_for('results'))
    try:
        # Fetch all riddles assigned to the user, not just uncompleted ones
        c.execute('''
            SELECT up.riddle_id, r.question, r.answer, r.hint1, r.hint2, r.hint3, 
                   up.hint1_used, up.hint2_used, up.hint3_used, up.completed, up.score
            FROM user_progress up
            JOIN riddles r ON up.riddle_id = r.id
            WHERE up.user_id = ? AND (r.image IS NULL OR r.image = '')
            ORDER BY up.riddle_id
        ''', (session['user_id'],))

        riddles = c.fetchall()

        if not riddles:
            return redirect(url_for('results'))

        riddles_with_variants = []

        for riddle in riddles:
            riddle_id = riddle['riddle_id']
            c.execute("SELECT question_variant FROM riddle_variants WHERE riddle_id = ?", (riddle_id,))
            variants = [row['question_variant'] for row in c.fetchall()]
            
            all_questions = variants + [riddle['question']]
            session_key = f"riddle_{session['user_id']}_{riddle_id}"

            if session_key not in session:
                session[session_key] = random.choice(all_questions)

            riddle_data = {
                'id': riddle_id,
                'riddle_id': riddle_id,
                'question': riddle['question'],
                'answer': riddle['answer'],
                'hint1': riddle['hint1'],
                'hint2': riddle['hint2'],
                'hint3': riddle['hint3'],
                'hint1_used': riddle['hint1_used'],
                'hint2_used': riddle['hint2_used'],
                'hint3_used': riddle['hint3_used'],
                'completed': riddle['completed'],
                'score': riddle['score']
            }

            riddle_data['display_question'] = session[session_key]
            riddles_with_variants.append(riddle_data)

        return render_template('test.html',
                               riddles_without_images=riddles_with_variants,
                               total_riddles=len(riddles_with_variants))

    except Exception as e:
        flash('An error occurred while loading the test.')
        print(f"Error: {str(e)}")
        return redirect(url_for('admin_dashboard'))

    finally:
        conn.close()


@app.route('/test_with_images') 
def test_with_images(): 
    if 'user_id' not in session: 
        flash('Please log in to take the test.') 
        return redirect(url_for('login')) 
    
    if has_completed_test(session['user_id']):
        flash('You have already completed this test. You cannot take it again.')
        return redirect(url_for('results'))
    
    conn = sqlite3.connect('riddle_test.db') 
    c = conn.cursor() 
    
    c.execute("SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND answer_attempt = 'FLAGGED-TAB-SWITCHING'", (session['user_id'],)) 
    if c.fetchone()[0] > 0: 
        conn.close() 
        flash('You have been flagged for tab switching.') 
        return redirect(url_for('results')) 
    
    c.execute(''' 
        SELECT r.id, r.question, r.image, up.score, up.completed, up.hint1_used, up.hint2_used, up.hint3_used 
        FROM riddles r 
        LEFT JOIN user_progress up ON r.id = up.riddle_id AND up.user_id = ? 
        WHERE r.image IS NOT NULL AND r.image != ''
        ORDER BY r.id 
    ''', (session['user_id'],)) 
    
    riddles = c.fetchall() 
    conn.close() 
    
    riddles_with_images = [
        {'id': r[0], 'question': r[1], 'image': r[2], 'score': r[3] or 10, 'completed': r[4] or 0,
         'hint1_used': r[5] or 0, 'hint2_used': r[6] or 0, 'hint3_used': r[7] or 0} for r in riddles
    ]
    
    return render_template('test_images.html', riddles_with_images=riddles_with_images)



@app.route('/get_hint_without_images/<int:riddle_id>/<int:hint_num>', methods=['POST'])
def get_hint_without_images(riddle_id, hint_num):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    conn = sqlite3.connect('riddle_test.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        c.execute('''
            SELECT r.hint1, r.hint2, r.hint3, up.hint1_used, up.hint2_used, up.hint3_used, up.score 
            FROM user_progress up
            JOIN riddles r ON up.riddle_id = r.id
            WHERE up.user_id = ? AND up.riddle_id = ? AND (r.image IS NULL OR r.image = '')
        ''', (session['user_id'], riddle_id))

        riddle = c.fetchone()
        if not riddle:
            return jsonify({"error": "Riddle not found or not applicable"}), 404

        hints = {1: 'hint1', 2: 'hint2', 3: 'hint3'}
        hint_used_keys = {1: 'hint1_used', 2: 'hint2_used', 3: 'hint3_used'}

        if hint_num not in hints:
            return jsonify({"error": "Invalid hint number"}), 400

        hint_key = hints[hint_num]
        hint_used_key = hint_used_keys[hint_num]

        if riddle[hint_used_key]:  
            return jsonify({"error": "Hint already used"}), 400

        hint_penalty = {1: 2, 2: 3, 3: 4}
        updated_score = max(1, riddle['score'] - hint_penalty[hint_num])  # Ensure min score is 1

        c.execute(f'''
            UPDATE user_progress 
            SET {hint_used_key} = 1, score = ? 
            WHERE user_id = ? AND riddle_id = ?
        ''', (updated_score, session['user_id'], riddle_id))

        conn.commit()

        return jsonify({
            "hint": riddle[hint_key],
            "updated_score": updated_score
        })

    except Exception as e:
        print(f"Error fetching hint: {str(e)}")
        return jsonify({"error": "Error fetching hint"}), 500

    finally:
        conn.close()


@app.route('/submit_answer_without_images/<int:riddle_id>', methods=['POST'])
def submit_answer_without_images(riddle_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    answer = request.json.get('answer', '').strip().lower()

    conn = sqlite3.connect('riddle_test.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        c.execute('''
            SELECT r.answer, up.completed, up.score 
            FROM user_progress up
            JOIN riddles r ON up.riddle_id = r.id
            WHERE up.user_id = ? AND up.riddle_id = ? AND (r.image IS NULL OR r.image = '')
        ''', (session['user_id'], riddle_id))

        riddle = c.fetchone()
        if not riddle:
            return jsonify({'error': 'Riddle not found'}), 404

        if riddle['completed']:  
            return jsonify({'error': 'Riddle already completed'}), 400

        correct_answer = riddle['answer'].strip().lower()
        is_correct = answer == correct_answer

        if is_correct:
            c.execute('''
                UPDATE user_progress 
                SET completed = 1, 
                    answer_attempt = ?, 
                    completion_time = ? 
                WHERE user_id = ? AND riddle_id = ?
            ''', (answer, datetime.now().isoformat(), session['user_id'], riddle_id))

            conn.commit()

            # Fetch the final score after hint deductions
            c.execute('''
                SELECT score FROM user_progress 
                WHERE user_id = ? AND riddle_id = ?
            ''', (session['user_id'], riddle_id))
            final_score = c.fetchone()['score']

            return jsonify({
                'correct': True,
                'final_score': final_score
            })
        else:
            c.execute("UPDATE user_progress SET answer_attempt = ? WHERE user_id = ? AND riddle_id = ?",
                      (answer, session['user_id'], riddle_id))
            conn.commit()

            return jsonify({'correct': False})

    except Exception as e:
        print(f"Error submitting answer: {str(e)}")
        return jsonify({'error': 'Error submitting answer'}), 500

    finally:
        conn.close()

@app.route('/get_hint_with_images/<int:riddle_id>/<int:hint_num>', methods=['POST'])
def get_hint_with_images(riddle_id, hint_num):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()

    # Check if the riddle has been completed; if yes, prevent hint usage
    c.execute("SELECT completed FROM user_progress WHERE user_id = ? AND riddle_id = ?", 
              (session['user_id'], riddle_id))
    result = c.fetchone()

    if result and result[0] == 1:  # If completed flag is 1, don't allow hints
        conn.close()
        return jsonify({'error': 'Riddle already completed'}), 400

    # Ensure the user has an entry in user_progress (reset hints if needed)
    c.execute("""
        SELECT hint1_used, hint2_used, hint3_used, score
        FROM user_progress WHERE user_id = ? AND riddle_id = ?
    """, (session['user_id'], riddle_id))
    user_progress = c.fetchone()

    if not user_progress:
        # If no progress exists, initialize it
        c.execute("""
            INSERT INTO user_progress (user_id, riddle_id, hint1_used, hint2_used, hint3_used, score, completed)
            VALUES (?, ?, 0, 0, 0, 10, 0)
        """, (session['user_id'], riddle_id))
        conn.commit()

    # Now, get the hint
    hint_column = f"hint{hint_num}"
    c.execute(f"SELECT {hint_column} FROM riddles WHERE id = ?", (riddle_id,))
    hint_data = c.fetchone()

    if not hint_data:
        conn.close()
        return jsonify({'error': 'Hint not found'}), 404

    hint = hint_data[0]

    # Check if the hint was already used
    if user_progress and user_progress[hint_num - 1] == 1:  # hint1_used is at index 0, hint2_used at index 1, etc.
        conn.close()
        return jsonify({'hint': hint, 'message': f'Hint {hint_num} was already used.'})

    # Calculate score reduction
    score_reduction = {1: 2, 2: 3, 3: 4}.get(hint_num, 0)

    # Update hint usage and deduct score
    update_query = f"""
        UPDATE user_progress 
        SET hint{hint_num}_used = 1, score = MAX(score - ?, 1) 
        WHERE user_id = ? AND riddle_id = ?
    """
    c.execute(update_query, (score_reduction, session['user_id'], riddle_id))

    conn.commit()

    # Fetch updated score
    c.execute("SELECT score FROM user_progress WHERE user_id = ? AND riddle_id = ?", 
              (session['user_id'], riddle_id))
    updated_score = c.fetchone()[0]

    conn.close()

    return jsonify({
        'hint': hint,
        'score_reduction': score_reduction,
        'updated_score': updated_score
    })


@app.route('/submit_answer_with_images/<int:riddle_id>', methods=['POST'])
def submit_answer_with_images(riddle_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    answer = request.json.get('answer', '').strip().lower()

    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()

    # Check if already completed
    c.execute("SELECT completed FROM user_progress WHERE user_id = ? AND riddle_id = ?",
             (session['user_id'], riddle_id))
    if c.fetchone()[0]:
        conn.close()
        return jsonify({'error': 'Riddle already completed'}), 400

    # Get correct answer
    c.execute("SELECT answer FROM riddles WHERE id = ?", (riddle_id,))
    correct_answer = c.fetchone()[0].lower()

    # Check answer
    is_correct = answer == correct_answer

    # Update user progress
    if is_correct:
        c.execute('''
            UPDATE user_progress 
            SET completed = 1, 
                answer_attempt = ?, 
                completion_time = ? 
            WHERE user_id = ? AND riddle_id = ?
        ''', (answer, datetime.now().isoformat(), session['user_id'], riddle_id))

        # Get current score
        c.execute("SELECT score FROM user_progress WHERE user_id = ? AND riddle_id = ?",
                 (session['user_id'], riddle_id))
        score = c.fetchone()[0]

        conn.commit()
        conn.close()

        return jsonify({
            'correct': True,
            'score': score
        })
    else:
        c.execute("UPDATE user_progress SET answer_attempt = ? WHERE user_id = ? AND riddle_id = ?",
                 (answer, session['user_id'], riddle_id))
        conn.commit()
        conn.close()

        return jsonify({
            'correct': False
        })
    
# Modify the results route to mark the test as completed when viewed
@app.route('/results')
def results():
    if 'user_id' not in session:
        flash('Please log in to view results.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()

    # Check if test was already completed
    c.execute("SELECT test_completed FROM users WHERE id = ?", (user_id,))
    test_completed = c.fetchone()[0]  

    # Only update if not already completed
    if not test_completed:
        c.execute("UPDATE users SET test_completed = 1 WHERE id = ?", (user_id,))
        conn.commit()
    
    # Fetch user's results
    c.execute('''
        SELECT r.id, r.question, r.answer, up.score, up.completed, 
               up.hint1_used, up.hint2_used, up.hint3_used, up.answer_attempt, up.completion_time
        FROM riddles r
        JOIN user_progress up ON r.id = up.riddle_id
        WHERE up.user_id = ?
        ORDER BY r.id
    ''', (user_id,))
    
    results_data = c.fetchall()

    # Calculate total score
    c.execute('''
        SELECT SUM(score)
        FROM user_progress
        WHERE user_id = ? AND completed = 1
    ''', (user_id,))
    
    total_score = c.fetchone()[0] or 0
    
    # Get total possible score
    c.execute("SELECT COUNT(*) * 10 FROM riddles")
    max_possible = c.fetchone()[0]

    # Calculate percentage score for progress bar
    percentage_score = int((total_score / max_possible) * 100) if max_possible > 0 else 0

    # Check if any riddles were flagged for cheating
    any_flagged = any(result[8] == "FLAGGED-TAB-SWITCHING" for result in results_data)

    conn.close()

    results = [{
        'id': result[0],
        'question': result[1],
        'correct_answer': result[2],
        'score': result[3],
        'completed': result[4],
        'hint1_used': result[5],
        'hint2_used': result[6],
        'hint3_used': result[7],
        'answer_attempt': result[8],
        'completion_time': result[9]
    } for result in results_data]

    return render_template('results.html', 
                           results=results, 
                           total_score=total_score, 
                           max_possible=max_possible,
                           percentage_score=percentage_score,
                           any_flagged=any_flagged,
                           test_completed=True)


# Add a route to check if all riddles are completed and redirect to results if so
@app.route('/check_test_completion')
def check_test_completion():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Check if all riddles are completed
    c.execute('''
        SELECT 
            (SELECT COUNT(*) FROM riddles) AS total_riddles,
            (SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND completed = 1) AS completed_riddles
    ''', (session['user_id'],))
    
    total_riddles, completed_riddles = c.fetchone()
    
    # If all riddles are completed, mark test as completed
    if total_riddles == completed_riddles:
        c.execute("UPDATE users SET test_completed = 1 WHERE id = ?", (session['user_id'],))
        conn.commit()
        conn.close()
        return jsonify({'completed': True, 'redirect': url_for('results')})
    
    conn.close()
    return jsonify({'completed': False})

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access.')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Get all users except admin
    c.execute('''
        SELECT u.id, u.username, u.email, 
               (SELECT COUNT(*) FROM user_progress WHERE user_id = u.id AND completed = 1) as completed_riddles,
               (SELECT SUM(score) FROM user_progress WHERE user_id = u.id AND completed = 1) as total_score
        FROM users u
        WHERE u.is_admin = 0
        ORDER BY total_score DESC
    ''')
    
    users_data = c.fetchall()
    
    # Get all riddles
    c.execute("SELECT id, question, answer FROM riddles ORDER BY id")
    riddles_data = c.fetchall()
    
    conn.close()
    
    users = []
    for user in users_data:
        users.append({
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'completed_riddles': user[3],
            'total_score': user[4] or 0
        })
    
    riddles = []
    for riddle in riddles_data:
        riddles.append({
            'id': riddle[0],
            'question': riddle[1],
            'answer': riddle[2]
        })
    
    return render_template('admin_dashboard.html', users=users, riddles=riddles)

@app.route('/admin/add_riddle', methods=['POST'])
def add_riddle():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
   
    # Get main riddle data
    primary_question = request.form.get('question')
    answer = request.form.get('answer')
    hint1 = request.form.get('hint1')
    hint2 = request.form.get('hint2')
    hint3 = request.form.get('hint3')
    image = request.files.get('image')  # Get image from request
   
    # Get question variants (if any)
    variant_questions = request.form.getlist('question_variants[]')  # Assuming you'll send variants as an array
    
    if not all([primary_question, answer, hint1, hint2, hint3]):
        return jsonify({'error': 'All fields are required'}), 400
        
    image_filename = None
    if image and image.filename:
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    try:
        # Add new riddle with image support (primary question stored in main table)
        c.execute('''
            INSERT INTO riddles (question, answer, hint1, hint2, hint3, image)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (primary_question, answer, hint1, hint2, hint3, image_filename))
       
        riddle_id = c.lastrowid
       
        # Insert any additional question variants
        for variant in variant_questions:
            if variant.strip():  # Only add non-empty variants
                c.execute('''
                    INSERT INTO riddle_variants (riddle_id, question_variant)
                    VALUES (?, ?)
                ''', (riddle_id, variant.strip()))
                
        # Initialize progress for all users
        c.execute("SELECT id FROM users WHERE is_admin = 0")
        user_ids = c.fetchall()
        for user_id in user_ids:
            c.execute("INSERT INTO user_progress (user_id, riddle_id) VALUES (?, ?)",
                     (user_id[0], riddle_id))
       
        conn.commit()
        return jsonify({
            'success': True,
            'riddle_id': riddle_id,
            'image_url': f"/static/uploads/{image_filename}" if image_filename else None,
            'variant_count': len(variant_questions)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/admin/get_riddle_variants/<int:riddle_id>', methods=['GET'])
def get_riddle_variants(riddle_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = sqlite3.connect('riddle_test.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        # Get the primary question
        c.execute("SELECT question FROM riddles WHERE id = ?", (riddle_id,))
        riddle = c.fetchone()
        
        if not riddle:
            return jsonify({'error': 'Riddle not found'}), 404
            
        primary_question = riddle['question']
        
        # Get all variants
        c.execute("SELECT id, question_variant as text FROM riddle_variants WHERE riddle_id = ?", 
                  (riddle_id,))
        variants = [dict(row) for row in c.fetchall()]
        
        return jsonify({
            'primary_question': primary_question,
            'variants': variants
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/admin/add_riddle_variant', methods=['POST'])
def add_riddle_variant():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    riddle_id = data.get('riddle_id')
    question_variant = data.get('question_variant')
    
    if not riddle_id or not question_variant:
        return jsonify({'error': 'Missing required fields'}), 400
        
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    try:
        # Check if riddle exists
        c.execute("SELECT id FROM riddles WHERE id = ?", (riddle_id,))
        if not c.fetchone():
            return jsonify({'error': 'Riddle not found'}), 404
            
        # Insert the new variant
        c.execute('''
            INSERT INTO riddle_variants (riddle_id, question_variant)
            VALUES (?, ?)
        ''', (riddle_id, question_variant))
        
        variant_id = c.lastrowid
        conn.commit()
        
        return jsonify({
            'success': True,
            'variant_id': variant_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/admin/delete_riddle/<int:riddle_id>', methods=['POST'])
def delete_riddle(riddle_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    try:
        # Delete user progress for this riddle
        c.execute("DELETE FROM user_progress WHERE riddle_id = ?", (riddle_id,))
        
        # Delete the riddle
        c.execute("DELETE FROM riddles WHERE id = ?", (riddle_id,))
        
        conn.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/admin/user_detail/<int:user_id>')
def user_detail(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access.')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Get user info
    c.execute("SELECT username, email FROM users WHERE id = ?", (user_id,))
    user_info = c.fetchone()
    
    if not user_info:
        conn.close()
        flash('User not found.')
        return redirect(url_for('admin_dashboard'))
    
    # Get user's results
    c.execute('''
        SELECT r.id, r.question, r.answer, up.score, up.completed, 
               up.hint1_used, up.hint2_used, up.hint3_used, up.answer_attempt, up.completion_time
        FROM riddles r
        JOIN user_progress up ON r.id = up.riddle_id
        WHERE up.user_id = ?
        ORDER BY r.id
    ''', (user_id,))
    
    results_data = c.fetchall()
    
    # Calculate total score
    c.execute('''
        SELECT SUM(score)
        FROM user_progress
        WHERE user_id = ? AND completed = 1
    ''', (user_id,))
    
    total_score = c.fetchone()[0] or 0
    
    # Get total possible score
    c.execute("SELECT COUNT(*) * 10 FROM riddles")
    max_possible = c.fetchone()[0]
    
    # Calculate percentage score for progress bar
    percentage_score = int((total_score / max_possible * 100)) if max_possible > 0 else 0
    
    conn.close()
    
    user = {
        'id': user_id,
        'username': user_info[0],
        'email': user_info[1]
    }
    
    results = []
    for result in results_data:
        results.append({
            'id': result[0],
            'question': result[1],
            'correct_answer': result[2],
            'score': result[3],
            'completed': result[4],
            'hint1_used': result[5],
            'hint2_used': result[6],
            'hint3_used': result[7],
            'answer_attempt': result[8],
            'completion_time': result[9]
        })
    
    return render_template('user_detail.html', 
                           user=user,
                           results=results, 
                           total_score=total_score, 
                           max_possible=max_possible,
                           percentage_score=percentage_score)
# Add a route to handle tab switching cheating attempts
@app.route('/record_cheating_attempt', methods=['POST'])
def record_cheating_attempt():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Add a cheating flag to all incomplete riddles
    c.execute('''
        UPDATE user_progress
        SET answer_attempt = "FLAGGED-TAB-SWITCHING"
        WHERE user_id = ? AND completed = 0
    ''', (session['user_id'],))
    
    # Mark test as completed
    c.execute("UPDATE users SET test_completed = 1 WHERE id = ?", (session['user_id'],))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})
    

@app.route('/admin/export_results')
def export_results():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Unauthorized access.')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    
    # Get all user results
    c.execute('''
        SELECT 
            u.id as user_id, 
            u.username, 
            u.email,
            r.id as riddle_id,
            r.question,
            r.answer as correct_answer,
            up.score,
            up.completed,
            up.hint1_used,
            up.hint2_used,
            up.hint3_used,
            up.answer_attempt,
            up.completion_time
        FROM users u
        JOIN user_progress up ON u.id = up.user_id
        JOIN riddles r ON up.riddle_id = r.id
        WHERE u.is_admin = 0
        ORDER BY u.id, r.id
    ''')
    
    columns = [desc[0] for desc in c.description]
    results = c.fetchall()
    
    conn.close()
    
    # Convert to list of dicts for JSON
    results_list = []
    for row in results:
        result_dict = {}
        for i, col in enumerate(columns):
            result_dict[col] = row[i]
        results_list.append(result_dict)
    
    return jsonify(results_list)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return redirect(url_for('static', filename=f'uploads/{filename}'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    if user_id == 1:
        return jsonify({'error': 'Cannot delete admin user'}), 400
    conn = sqlite3.connect('riddle_test.db')
    c = conn.cursor()
    try:
        c.execute('DELETE FROM user_progress WHERE user_id = ?', (user_id,))
        c.execute('DELETE FROM user_question_variants WHERE user_id = ?', (user_id,))
        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)