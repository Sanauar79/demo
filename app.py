from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User , Contact
from flask_migrate import Migrate
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import csv
import io
from flask import send_file

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
    messages = Contact.query.filter_by(user_id=user.id).all()
    message_count = len(messages)
    return render_template('user_dashboard.html' , user=user,messages=messages,message_count=message_count)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    errors = {}

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        phone = request.form.get('phone', '').strip()
        message = request.form.get('message', '').strip()
    

        # Simple validation
        if not name:
            errors['name'] = 'Name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        if not message:
            errors['message'] = 'Message is required.'

        if not errors:
            user = None
            if 'email' in session:
                user = User.query.filter_by(email=session['email']).first()
            new_contact = Contact(
                name=name,
                email=email,
                address=address,
                phone=phone,
                message=message,
                user_id=user.id if user else None
                 
            )
            db.session.add(new_contact)
            db.session.commit()

            send_email_to_user(
            name=name,
            to_email=email
           )

            send_email_to_admin(
              name=name,
              email=email,
              phone=phone,
              message=message
        )

            # flash('Your message has been sent successfully.', 'success')
            return redirect(url_for('user_dashboard'))

    return render_template('contact.html', errors=errors)

@app.route('/admin/messages')
def admin_messages():
    if 'email' not in session:
        flash("Please log in first.", "danger")
        return redirect('/login')
    messages = Contact.query.order_by(Contact.id.desc()).all()
    return render_template('admin_messages.html', messages=messages)

@app.route('/delete_message/<int:message_id>', methods=['GET'])
def delete_message(message_id):
    message = Contact.query.get_or_404(message_id)
    db.session.delete(message)
    db.session.commit()
    flash('Message deleted successfully.', 'success')
    return redirect(url_for('admin_messages')) 

@app.route('/update_message/<int:message_id>', methods=['GET', 'POST'])
def update_message(message_id):
    message = Contact.query.get_or_404(message_id)
    errors = {}

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        phone = request.form.get('phone', '').strip()
        message_text = request.form.get('message', '').strip()

      
        if not name:
            errors['name'] = 'Name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        if not message_text:
            errors['message'] = 'Message is required.'

        if not errors:
            message.name = name
            message.email = email
            message.address = address
            message.phone = phone
            message.message = message_text
            db.session.commit()
            # flash('Message updated successfully.', 'success')
            return redirect(url_for('admin_messages'))  

        return render_template('update_message.html', message=message, errors=errors)

    return render_template('update_message.html', message=message, errors=errors)



def send_email_to_user(name, to_email):
    subject = "Thank you for contacting us"
    body = f"""
    Hi {name},

    Thanks for reaching out to us. We have received your message and will get back to you soon.

    Best regards,
    CRUD Team
    """
    send_email(to_email, subject, body)


def send_email_to_admin(name, email, phone, message):
    subject = "New Contact Form Submission"
    body = f"""
    A new contact form has been submitted:

    Name: {name}
    Email: {email}
    Phone: {phone}
    Message:
    {message}
    """
    admin_email = "sanauarh@gmail.com" 
    send_email(admin_email, subject, body)

def send_email(to_email, subject, body):
    sender_email = "sanauarh@gmail.com"
    sender_password = "kftpwzpgeymcwutj" 

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")


@app.route('/admin/export')
def export_messages():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['ID', 'Name', 'Email', 'Message'])
    messages = Contact.query.all()
    for msg in messages:
        writer.writerow([msg.id, msg.name, msg.email,msg.phone, msg.message])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        download_name='contact_messages.csv',
        as_attachment=True
    )



@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# ✅ Correct place to initialize the DB and run the server
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
