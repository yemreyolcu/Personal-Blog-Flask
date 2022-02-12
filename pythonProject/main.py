from functools import wraps

from flask import Flask, render_template, flash, redirect, url_for, session, request
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from wtforms import Form, StringField, TextAreaField, PasswordField, validators


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_id" in session:
            return f(*args, **kwargs)
        else:
            flash("Lütfen giriş yapın.", "danger")
            return redirect(url_for("login"))

    return decorated_function


class registerForm(Form):
    name = StringField("İsim", validators=[validators.Length(min=4, max=20)])
    username = StringField("Kullanıcı Adı", validators=[validators.Length(min=4, max=20)])
    email = StringField("E-mail", validators=[validators.Email(message="Please enter valid e-mail..")])
    password = PasswordField("Şifre", validators=[validators.DataRequired(message="Please enter password"),
                                                  validators.EqualTo(fieldname="confirm", message="Try again..")])
    confirm = PasswordField("Şifreyi Onayla")


class loginForm(Form):
    username = StringField("Kullanıcı Adı : ")
    password = PasswordField("Şifre : ")


class articleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.Length(min=10, max=125)])
    content = TextAreaField("Makale İçeriği", validators=[validators.Length(min=5)])


app = Flask(__name__)
app.secret_key = "yeyblog"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "yeyblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = registerForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        cursor = mysql.connection.cursor()
        answ = "Insert into users (name,email,username,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(answ, (name, username, email, password))
        mysql.connection.commit()
        cursor.close()

        flash("Tebrikler, başarıyla kayıt oldunuz. ", "success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = loginForm(request.form)
    if request.method == "POST":
        usernameEnter = form.username.data
        passwordEnter = form.password.data
        cursor = mysql.connection.cursor()
        answ = "Select * From users where username = %s"
        result = cursor.execute(answ, (usernameEnter,))
        if result > 0:
            data = cursor.fetchone()
            realPassword = data["password"]
            if sha256_crypt.verify(passwordEnter, realPassword):
                flash("Başarıyla giriş yapıldı. ", "success")
                session["logged_in"] = True
                session["username"] = usernameEnter
                return redirect(url_for("index"))
            else:
                flash("Hatalı giriş. Lütfen tekrar deneyin. ", "danger")
        else:

            flash("Hatalı giriş. Lütfen tekrar deneyin. ", "danger")
            return redirect(url_for("login"))
    return render_template("login.html", form=form)


@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    answ = "Select * From articles"
    result = cursor.execute(answ)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles=articles)
    else:
        return render_template("articles.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Başarıyla çıkış yapıldı.", "success")
    return redirect(url_for("index"))


@login_required
@app.route("/dashboard")
def dashboard():
    cursor = mysql.connection.cursor()
    answ = "Select * From articles where author = %s"
    result = cursor.execute(answ, (session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")


@app.route("/addarticle", methods=["GET", "POST"])
def addarticle():
    form = articleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        answ = "Insert into articles (title,author,content) VALUES (%s,%s,%s)"
        cursor.execute(answ, (title, session["username"], content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale eklendi ", "success")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html", form=form)

@app.route("/article/<string:id>")
def detailarticle(id):
    cursor = mysql.connection.cursor()
    answ = "Select * From articles where id = %s"
    result = cursor.execute(answ,(id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")


@login_required
@app.route("/del/<string:id>")
def delete(id):
    cursor = mysql.connection.cursor()
    answ = "Select * from articles where author = %s and id = %s"
    result = cursor.execute(answ,(session["username"],id))
    if result > 0:
        answ2 = "Delete from articles where id = %s"
        cursor.execute(answ2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Makaleyi silme yetkiniz yok veya makale mevcut değil.","danger")
        return redirect(url_for("index"))


@login_required
@app.route("/edit/<string:id>",methods = ["GET","POST"])
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        answ = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(answ,(id,session["username"]))
        if result != 0:
            article = cursor.fetchone()
            form = articleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form=form)
        else:
            flash("Makale yok veya yetkiniz yok.","danger")
            return redirect(url_for("index"))
    else:
        form = articleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        answ2 = "Update articles Set title = %s,content = %s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(answ2,(newTitle,newContent,id))
        mysql.connection.commit()
        flash("Makale başarıyla güncellendi","success")
        return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
