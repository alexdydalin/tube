import os
from flask import Flask, render_template, request, flash, redirect, url_for, g, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import datetime
from functools import wraps
from werkzeug.datastructures import FileStorage
from s3_config import s3_form_field

app = Flask(__name__)

app.secret_key = '0595018d9ece1ec1927644f7704725a70ef3c48e'  # import os // os.urandom(20).hex()

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///py_modules.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy()
db.init_app(app)

manager = LoginManager(app)
manager.login_view = 'sign_in'
manager.login_message = "Авторизируйтесь для дуступа ко всем страницам"
manager.login_message_category = "success"

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def is_photo(filename):
    photo_file_format = {'png', 'jpg', 'jpeg'}
    return '.' in filename and filename.rsplit('.', 1)[1] in photo_file_format


def is_video(filename):
    video_file_format = {'mp4'}
    return '.' in filename and filename.rsplit('.', 1)[1] in video_file_format


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), nullable=False)
    login = db.Column(db.String(128), nullable=False, unique=True)
    email = db.Column(db.String(128), nullable=False, unique=True)
    hashed_password = db.Column(db.String(256), nullable=False)
    admin = db.Column(db.Boolean, default=False)
    avatar_link = db.Column(db.String(128))

    def is_admin(self):
        return self.admin


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename_uuid = db.Column(db.String(128))
    filename = db.Column(db.String(128))
    title = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.String(128), nullable=False)
    user_login = db.Column(db.String(128), nullable=False)
    video_link = db.Column(db.String(128))
    poster_link = db.Column(db.String(128))
    upload_on = db.Column(db.String(128))


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_login = db.Column(db.String, db.ForeignKey('user.login', ondelete='CASCADE'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id', ondelete='CASCADE'), nullable=False)
    press_like = db.Column(db.Boolean, default=False)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_login = db.Column(db.String(128), db.ForeignKey('user.login', ondelete='CASCADE'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id', ondelete='CASCADE'), nullable=False)
    comment = db.Column(db.Text)
    upload_on_date = db.Column(db.String(128))
    upload_on_time = db.Column(db.String(128))


def admin_login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_admin:
            return abort(403)
        return func(*args, **kwargs)

    return decorated_view


def create_admin():
    email = 'admin@admin.com'
    username = 'admin'
    login = 'admin'
    password = 'admin1'
    admin = True
    try:
        password_hash = generate_password_hash(password)
        new_user = User(email=email, username=username,
                        login=login, hashed_password=password_hash,
                        admin=admin, avatar_link='../static/img/avatar.jpeg')
        db.session.add(new_user)
        db.session.commit()
    except:
        db.session.rollback()


@manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
@app.route('/sign-in', methods=['POST', 'GET'])
def sign_in():
    if current_user.is_authenticated:
        return redirect(url_for('profile', login=current_user.login))
    if request.method == 'POST':
        login = (str(request.form.get('login'))).lower().strip()
        password = request.form.get('password')
        if not (login or password):
            flash("Заполните поля логина и пароля")
        else:
            user = User.query.filter_by(login=login).first()
            if user and check_password_hash(user.hashed_password, password):
                remember_me = True if request.form.get('remainme') else False
                login_user(user, remember=remember_me)

                return redirect(request.args.get('next') or url_for('main'))

            flash("Неверное имя пользователя или пароль")

    return render_template('sign_in.html', title='Вход')


@app.route('/sign-up', methods=['POST', 'GET'])
def sign_up():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        login = (str(request.form['login'])).lower().strip()
        password = request.form['password']

        if ('admin' in login or 'admin' in username or 'Admin' in username):
            flash("Введите другой логин или имя пользователя")
        elif not (email or password or username or login):
            flash("Заполните все поля!")
        elif not ('@' in email or '.' in email or len(email) >= 1):
            flash("Заполните все поля правильно!")
        elif len(login) < 3 or len(password) < 3:
            flash("Логин и пароль должны быть более трех символов")
        else:
            try:
                password_hash = generate_password_hash(password)
                new_user = User(email=email, username=username,
                                login=login, hashed_password=password_hash,
                                avatar_link='../static/img/avatar.jpeg')


                db.session.add(new_user)
                db.session.commit()

                flash("Вы успешно зарегистрированы!")
                return redirect(url_for('sign_in'))
            except:
                db.session.rollback()
                flash("Ошибка регистрации, пользователь с такими данными уже существует")

    return render_template('sign_up.html', title='Регистрация')


@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('sign_in'))


@app.route('/main')
def main():
    if current_user.is_authenticated:
        videos = Video.query.all()
        return render_template('main.html', videos=videos)
    return redirect(url_for('sign_in'))


UPLOAD_FOLDER = 'static/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/profile/<login>', methods=['POST', 'GET'])
@login_required
def profile(login):
    user = User.query.filter_by(login=login).first()
    if user is None:
        flash('Пользователь "' + login + '" не найден')
        return render_template('404.html')
    if current_user.login != 'admin' and login == 'admin':
        flash('У вас нет доступа к этому разделу')
        return render_template('404.html')

    user_videos = Video.query.filter_by(user_login=login).all()
    if current_user.login == login:
        if request.method == 'POST':
            avatar = request.files['avatar']

            avatar.save(os.path.join('./static/avatars/', current_user.login + '.jpeg'))
            avatar_link = '../static/avatars/' + current_user.login + '.jpeg'
            user.avatar_link = avatar_link
            try:
                db.session.commit()
            except:
                flash('Ошибка при загрузке аватарки')
                return redirect(url_for('error_404'))
            return redirect(url_for('profile', login=current_user.login))

    return render_template('profile.html', user=user, videos=user_videos)


@app.route('/make_as_admin/<login>', methods=['POST', 'GET'])
@login_required
def make_as_admin(login):
    user = User.query.filter_by(login=login).first()
    if current_user.login == 'admin':
        if login.admin == False:
            user.admin = True
        else:
            user.admin = False
    return redirect(url_for('profile', login))


@app.route('/upload', methods=['POST', 'GET'])
@login_required
def upload():
    #    filenameuuid = uuid.uuid4().hex
    #    if request.method == 'POST':
    #        #if not allowed_file(uploaded_file.filename):
    #        #    return "FILE NOT ALLOWED!"
    #    # https://tube.storage.yandexcloud.net/videos/$f2b677ed942e494cbed999d613b1cd5c.mp4
    #        title = request.form["title"]
    #        description = request.form["description"]
    #    #s3 = boto3.client('s3',
    #    #                    aws_access_key_id='YCAJEFJ3M9_0-1HtwTzDx9vmM',
    #    #                    aws_secret_access_key='YCNv0AroQBpLdcYFsSX7SNBpoJMao85Vdxog7aOp')
    #    #response = s3.put_object(
    #    #    Body=uploaded_file,
    #    #    Bucket='tube',
    #    #    Key='video')
    #        info = Video_info(title=title, description=description)
    #        db.session.add(info)
    #        db.session.commit()
    #
    #    #return redirect(url_for("upload"), link=link)
    #        #return redirect(url_for('upload'))
    #    link = str('https://tube.storage.yandexcloud.net/videos/$' + filenameuuid + '.mp4')
    #    href = Video_link(link=link, filenameuuid=filenameuuid)
    #    db.session.add(href)
    #    db.session.commit()
    #    return render_template("upload.html", filenameuuid=filenameuuid)

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Не могу прочитать файл')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '' or file.filename is None:
            flash('Нет выбранного файла')
            return redirect(request.url)
        if file and is_video(file.filename):
            filename = secure_filename(file.filename)
            filename_uuid = uuid.uuid4().hex
            title = request.form['title']
            if title == '' or title is None:
                flash('Введите название для видео!')
                return redirect(request.url)
            description = request.form['description']
            video_link = 'static/videos/' + filename_uuid + '.mp4'
            user_id = current_user.id
            user_login = current_user.login

            poster = request.files['poster']

            if not poster:
                poster_link = 'static/poster/filler_poster.jpeg'
            else:
                poster_link = 'static/poster/' + filename_uuid + '.jpeg'
                poster.save(os.path.join(app.config['UPLOAD_FOLDER'] + 'poster', filename_uuid + '.jpeg'))

            upload_on = str(datetime.datetime.now())
            upload_on = upload_on[8:10] + '.' + upload_on[5:7] + '.' + upload_on[0:4]
            new_video = Video(filename=filename, filename_uuid=filename_uuid,
                              title=title, description=description,
                              video_link=video_link, user_id=user_id,
                              user_login=user_login, poster_link=poster_link,
                              upload_on=upload_on
                              )
            try:
                db.session.add(new_video)
                db.session.commit()
            except:
                flash('Ошибка при загрузке видео')
                return redirect(url_for('error_404'))

            file.save(os.path.join(app.config['UPLOAD_FOLDER'] + 'videos/', filename_uuid + '.mp4'))

            flash('Видео загружено!')
            return redirect(url_for('upload'))
    return render_template('uplnew.html')


@app.route('/watch/<filename_uuid>', methods=['POST', 'GET'])
@login_required
def watch(filename_uuid):
    file = Video.query.filter_by(filename_uuid=filename_uuid).first()
    if file is None or file == 0:
        flash('Видео не найдено')
        return redirect(url_for('error_404'))
    comments = Comment.query.filter_by(video_id=filename_uuid).all()
    uploader = file.user_login
    uploader = User.query.filter_by(login=uploader).first()
    if request.method == 'POST':
        try:
            comment = request.form['comment']
            upload_on = str(datetime.datetime.now())
            upload_on_date = upload_on[8:10] + '.' + upload_on[5:7] + '.' + upload_on[0:4]
            upload_on_time = upload_on[10:16]
            new_comment = Comment(user_login=current_user.login, video_id=filename_uuid,
                                  comment=comment, upload_on_date=upload_on_date,
                                  upload_on_time=upload_on_time
                                  )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('watch', filename_uuid=file.filename_uuid))
        except:
            flash('Ошибка при сохранении комментария')
            return redirect(url_for('error_404'))
    return render_template('watch.html', file=file, comments=comments, uploader=uploader, user=uploader )


@app.route('/video/<filename_uuid>/delete')
@login_required
def video_delete(filename_uuid):
    video_to_delete = Video.query.filter_by(filename_uuid=filename_uuid).first()
    try:
        video_link = app.config['UPLOAD_FOLDER'] + 'videos/' + filename_uuid + '.mp4'
        try:
            os.remove(video_link)
        except:
            pass
        db.session.delete(video_to_delete)
        db.session.commit()
        flash('Видео успешно удалено')
        return redirect(url_for('profile', login=current_user.login))
    except:
        flash('Ошибка при удалении видео')
        return redirect(url_for('error_404'))


@app.route('/comment/<filename_uuid>/<login>/delete')
@login_required
def comment_delete(filename_uuid, login):
    comments_to_delete = Comment.query.filter_by(video_id=filename_uuid, user_login=login).all()
    try:
        for comment in comments_to_delete:
            db.session.delete(comment)
        db.session.commit()
        return redirect(url_for('watch', filename_uuid=filename_uuid))
    except:
        flash('Ошибка при удалении комментария')
        return redirect(url_for('error_404'))


@app.route('/404')
def error_404():
    return render_template('404.html')


with app.app_context():
    if __name__ == "__main__":
        db.create_all()
        create_admin()
        app.run()
