from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User
from flask_migrate import Migrate
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'sanauarh@gmail.com'
app.config['MAIL_PASSWORD'] = 'kftpwzpgeymcwutj'  
app.config['MAIL_DEFAULT_SENDER'] = 'sanauarh@gmail.com'
mail = Mail(app)

serializer = URLSafeTimedSerializer(app.secret_key)

# Configure SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    errors = {}
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template('login.html',errors=errors)

        user = User.query.filter_by(email=email).first()

        if user:
           
            if not user.is_verified:
                flash('Please verify your email before logging in.', 'warning')
                return render_template('login.html',errors=errors)

           
            if user.check_password(password):
                session['email'] = user.email
                session['role'] = user.role  


         
            if user.role == 'admin':
                return redirect('/admin_dashboard')
            else:
                return redirect('/user_dashboard')
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html',errors=errors)

@app.route('/register', methods=['GET', 'POST'])
def register():
    errors = {}

    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password'].strip()

        if not name:
            errors['name'] = 'Name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        elif User.query.filter_by(email=email).first():
            errors['email'] = 'Email already exists.'
        if not password:
            errors['password'] = 'Password is required.'
        elif len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters.'

        if not errors:
            new_user = User(name=name, email=email,role='user')
            new_user.set_password(password) 
            db.session.add(new_user)
            db.session.commit()

            # Generate token
            token = serializer.dumps(email, salt='email-confirm')

            # Create verification link
            confirm_url = url_for('confirm_email', token=token, _external=True)

            # Send email
            msg = Message('Please confirm your email', recipients=[email])
            msg.body = f'Hi {name},\n\nPlease confirm your email by clicking the link:\n{confirm_url}\n\nThank you!'
            mail.send(msg)

            flash('Registration successful. Please check your email to confirm.', 'info')
            return redirect('/register')
        return render_template('register.html', errors=errors)
    return render_template('register.html', errors={})

    

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)  
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect('/login')

    user = User.query.filter_by(email=email).first_or_404()
    if user.is_verified:
        flash('Account already confirmed. Please login.', 'success')
    else:
        user.is_verified = True
        db.session.commit()
        flash('Email confirmed. You can now login.', 'success')

    return redirect('/login')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'email' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect('/login')
    
    user = User.query.filter_by(email=session['email']).first()
    users = User.query.all()
    return render_template('admin_dashboard.html', user=user , users=users)


@app.route('/user_dashboard')
def user_dashboard():
    if 'email' not in session or session.get('role') != 'user':
        flash('Access denied.', 'danger')
        return redirect('/login')
    
    user = User.query.filter_by(email=session['email']).first()
    # messages = Contact.query.filter_by(user_id=user.id).all()
    # message_count = len(messages)
    return render_template('user_dashboard.html' , user=user)



@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# ✅ Correct place to initialize the DB and run the server
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
