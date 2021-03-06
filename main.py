from flask import Flask, render_template, redirect, session, url_for, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, SelectField,\
    FileField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Length, ValidationError
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from config import configs
from datetime import datetime
import os
from flask_restful import reqparse, abort, Api, Resource


app = Flask(__name__)
api = Api(app, catch_all_404s=True)

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
        return '<News {} {}>'.format(self.id, self.title)


def abort_if_news_not_found(news_id):
    if not News.query.get(news_id):
        abort(404, message="News {} not found".format(news_id))


def abort_if_user_not_found(user_id):
    if not News.query.get(user_id):
        abort(404, message="User {} not found".format(user_id))


class NewsApi(Resource):
    def get(self, news_id):
        abort_if_news_not_found(news_id)

        news = News.query.get(news_id)
        res = {
            'title': news.title,
            'date': news.date,
            'user_id': news.user_id
        }

        return jsonify({'news': res})

    def delete(self, news_id):
        abort_if_news_not_found(news_id)

        news = News.query.get(news_id)
        db.session.delete(news)
        db.session.commit()

        return jsonify({'success': 'OK'})


class NewsListApi(Resource):
    def get(self):
        news_list = News.query.all()

        res = []
        for news in news_list:
            res.append({
                    'title': news.title,
                    'date': news.date,
                    'user_id': news.user_id
                })

        return jsonify({'news': res})


class UserApi(Resource):
    def get(self, user_id):
        abort_if_user_not_found(user_id)

        user = User.query.get(user_id)
        res = {
            'username': user.username
        }

        return jsonify({'user': res})


class UserListApi(Resource):
    def get(self):
        user_list = User.query.all()

        res = []
        for user in user_list:
            res.append({
                    'username': user.username
                })

        return jsonify({'users': res})


api.add_resource(NewsListApi, '/news_api')
api.add_resource(NewsApi, '/news_api/<int:news_id>')
api.add_resource(UserListApi, '/users_api')
api.add_resource(UserApi, '/user_api/<int:user_id>')


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


def validate_login(form, submit):
    """Проверяет, вошел ли пользователь в аккаунт"""
    if 'username' not in session:
        raise ValidationError('Войдите в аккаунт')


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


class AddNewsForm(FlaskForm):
    category = SelectField('Категория', choices=[
        ('Футбол', 'Футбол'), ('Формула 1', 'Формула 1')])
    photo = FileField('Фотография', validators=[DataRequired()])
    title = StringField('Заголовок', validators=[DataRequired()])
    content = TextAreaField('Текст', validators=[DataRequired()])
    submit = SubmitField('Добавить', validators=[validate_login])


class EditNewsForm(FlaskForm):
    category = SelectField('Категория', choices=[
        ('Футбол', 'Футбол'), ('Формула 1', 'Формула 1')])
    photo = FileField('Фотография')
    title = StringField('Заголовок')
    content = TextAreaField('Текст')
    submit = SubmitField('Изменить', validators=[validate_login])


@app.route('/add_news', methods=['GET', 'POST'])
def add_news():
    form = AddNewsForm()

    if form.validate_on_submit():
        im = form.photo.data
        photo_path = os.path.join('static/img', im.filename)
        im.save(photo_path)

        date = str(datetime.now()).split('.')[0]

        news = News(
            title=form.title.data,
            category=form.category.data,
            content=form.content.data,
            user_id=session['user_id'],
            photo=os.path.join('img', im.filename),
            date=date,
        )
        db.session.add(news)
        db.session.commit()

        return redirect('/success')
    return render_template(
        'add_news.html', title='Добавить новость', form=form)


@app.route('/news/<int:news_id>', methods=['GET', 'POST'])
def news(news_id):
    news = News.query.get(news_id)
    # В news.photo неправильно указан адрес при работе в news.html
    news.photo = url_for('static', filename=news.photo)

    author = User.query.get(news.user_id).username

    return render_template(
        'news.html', title='Новость', news=news, author=author)


@app.route('/edit_news/<int:news_id>', methods=['GET', 'POST'])
def edit_news(news_id):
    form = EditNewsForm()

    if form.validate_on_submit():
        news = News.query.get(news_id)

        im = form.photo.data
        if im:
            photo_path = os.path.join('static/img', im.filename)
            im.save(photo_path)

            news.photo = os.path.join('img', im.filename)

        title = form.title.data
        if title:
            news.title = title

        news.category = form.category.data

        content = form.content.data
        if content:
            news.content = content

        db.session.commit()
        return redirect('/success')
    return render_template(
        'edit_news.html', title='Изменить новость', form=form,
        news_id=news_id)


@app.route('/delete_news/<int:news_id>', methods=['GET', 'DELETE'])
def delete_news(news_id):
    news = News.query.get(news_id)
    db.session.delete(news)
    db.session.commit()

    return redirect('/success')


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


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    news_list = News.query.all()

    # Указываем правильный путь к изображению
    for news in news_list:
        news.photo = url_for('static', filename=news.photo)

    news_list.sort(key=lambda x: x.id, reverse=True)

    return render_template('index.html', title='Главная', news=news_list)


@app.route('/football', methods=['GET', 'POST'])
def footbal():
    news_list = News.query.filter_by(category='Футбол').all()

    # Указываем правильный путь к изображению
    for news in news_list:
        news.photo = url_for('static', filename=news.photo)

    news_list.sort(key=lambda x: x.id, reverse=True)

    return render_template('index.html', title='Футбол', news=news_list)


@app.route('/formula', methods=['GET', 'POST'])
def formula():
    news_list = News.query.filter_by(category='Формула 1').all()

    # Указываем правильный путь к изображению
    for news in news_list:
        news.photo = url_for('static', filename=news.photo)

    news_list.sort(key=lambda x: x.id, reverse=True)

    return render_template('index.html', title='Формула 1', news=news_list)


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


@app.route('/user/<int:user_id>')
def user(user_id):
    news_list = News.query.filter_by(user_id=session['user_id'])

    return render_template(
        'user.html', title=session['username'], news_list=news_list)


if __name__ == '__main__':
    app.run(debug=True)
