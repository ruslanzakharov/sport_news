from flask import Flask, render_template, redirect, session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length, ValidationError
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from config import configs


app = Flask(__name__)
for key in configs.keys():
    app.config[key] = configs[key]

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(80), unique=False, nullable=False)

    def __repr__(self):
        return '<User {} {}>'.format(self.id, self.username)


class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(80), unique=False, nullable=False)
    category = db.Column(db.String(80), unique=False, nullable=False)
    title = db.Column(db.String(120), unique=False, nullable=False)
    photo = db.Column(db.String(120), unique=False, nullable=False)
    content = db.Column(db.String(1024), unique=False, nullable=False)

    user_id = db.Column(db.Integer,
                        db.ForeignKey('user.id'),
                        nullable=False)
    user = db.relationship('User', backref=db.backref('news', lazy=True))

    def __repr__(self):
        return 'News {} {}'.format(self.id, self.title)


def validate_password(form, password):
    """Проверяет хеши паролей"""
    user = User.query.filter_by(username=form.username.data).first()
    if not user:
        raise ValidationError('Пользователь не существует')
    if not check_password_hash(user.password_hash, password.data):
        raise ValidationError('Неверный пароль')


def validate_username(form, username):
    """Проверяет существование пользователя"""
    if User.query.filter_by(username=username.data).first():
        raise ValidationError('Пользователь существует')


class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[
        DataRequired(), validate_password])
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', [
        Length(min=4, max=25), validate_username])
    password = PasswordField('Пароль', [Length(min=6, max=35)])
    submit = SubmitField('Зарегистрироваться')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        password_hash = generate_password_hash(password)

        user = User(username=username, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()

        return redirect('/success')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Главная')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        session['username'] = form.username.data
        session['user_id'] = User.query.filter_by(
            username=session['username']).first().id

        return redirect('/success')
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/success')
def success():
    return render_template('success.html', title='Успех')


@app.route('/logout')
def logout():
    session.pop('username', 0)
    session.pop('user_id', 0)
    return redirect('/login')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8082)
