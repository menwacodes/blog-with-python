from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_moment import Moment
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import text
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegistrationForm, LoginForm, CommentForm
from functools import wraps

from flask_gravatar import Gravatar
import os

from sendEmail import send_email

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET-KEY', 'cZzDjeWfBKFZ_CKJWbbfDeEWoybK1fKpaX9cKKqGbvc')
app.config['CKEDITOR_PKG_TYPE'] = 'standard'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL",  "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# WRAP APP IN LOGIN - required for conditional rendering based on user login status
login_manager = LoginManager()
login_manager.init_app(app)

# WRAP APP IN GRAVATAR
gravatar = Gravatar(app, size=50, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

# WRAP APP IN MOMENT
moment = Moment(app)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


##CONFIGURE TABLES

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")

    comments = relationship("Comment", back_populates="user")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    # for comments
    comments = relationship("Comment", back_populates="post")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    # for blog
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    post = relationship("BlogPost", back_populates="comments")
    # for comments
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = relationship("User", back_populates="comments")

db.create_all()


# User.__table__.create(db.session.bind)

# CUSTOM ADMIN DECORATOR
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If user is anon or logged in and not admin, abort
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Get form data
        frm_email = form.email.data
        frm_pw = form.password.data
        frm_name = form.name.data

        # Check to see if unique email exists
        check_user = User.query.filter_by(email=frm_email).first()

        if check_user:
            flash(f"{frm_email} already exists, please login")
            return redirect(url_for('login'))

        # Salt and Hash password
        password = generate_password_hash(password=frm_pw,
                                          method="pbkdf2:sha256",
                                          salt_length=8)

        # Create and save user
        new_user = User(
            email=frm_email,
            password=password,
            name=frm_name
        )
        db.session.add(new_user)
        db.session.commit()

        # Log user in
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    # POST
    if form.validate_on_submit():
        # Get form data
        frm_email = form.email.data
        frm_pw = form.password.data

        # See if user exists
        user = User.query.filter_by(email=frm_email).first()
        if user:
            # Check Password
            if check_password_hash(user.password, frm_pw):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                send_message = True
        else:
            send_message = True
        if send_message:
            flash('Invalid Credentials')
            return redirect(url_for('login'))
    # GET
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        # Ensure poster is logged in
        if not current_user.is_authenticated:
            flash("You need to login or register to comment")
            return redirect(url_for('login'))

        # save to the database
        post_text = form.body.data
        user_id = current_user.id
        post_id = post_id
        comment = Comment(post_id=post_id, user_id=user_id, text=post_text)
        db.session.add(comment)
        db.session.commit()

    # Build up comments and send to page

    comments = db.session.query('text', 'email', 'name')\
        .from_statement(text(f"SELECT C.TEXT as text, "
                             f"U.EMAIL as email, "
                             f"U.NAME as name "
                             f"FROM COMMENTS C, USERS U "
                             f"WHERE C.USER_ID=U.ID "
                             f"AND C.POST_ID={post_id}"))\
        .all()
    # comments.reverse()  # use if want most recent comments at the top as comments is list

    return render_template("post.html", post=requested_post, form=form, comments=comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    if request.method == 'POST':
        greeting = "Successfully sent your message"
        # Grab form data
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        message = request.form['message']

        # Create email fields
        subject = f"Blog message from {name}"
        content = f"Message:\n{message}\n\nEmail: {email}\n\nPhone: {phone}"

        # Send email
        send_email(subject, content)
        return render_template('contact.html', greeting=greeting)

    elif request.method == 'GET':
        greeting = "Contact Me"
        return render_template('contact.html', greeting=greeting)


@app.route("/new-post", methods=['GET', 'POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
