import os
import requests
from datetime import datetime
from passlib.hash import sha256_crypt
from flask import request, jsonify
from flask import Flask, flash, render_template
from flask import Flask, session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#Register the user
@app.route("/userregister", methods=["POST"])
def userregister():
   
   # Get the data from user registration form
    error = None
    username = request.form.get("username")
    password = request.form.get("password")
    confirmPassword=request.form.get("confirmPassword")
    name = request.form.get("name")
    email = request.form.get("email")
    h = sha256_crypt.encrypt(password)

    # Validate the data from the form

    if username=='' or password =='' or name=='' or email=='' :
        error='You need to fill all the fields !'
        return render_template("register.html", error=error)
    elif db.execute("SELECT * FROM users WHERE username =:username",{"username": username}).rowcount >0 :
         error= 'username is not available'
         
         return render_template("register.html", error=error)
    elif password != confirmPassword:
        error= 'Password is not match with the Confirm Password'
        return render_template("register.html", error=error)

        # Create the user and update the table
    else:
        try:
            db.execute("INSERT INTO users(username,password,name,email) VALUES (:username, :password, :name,:email)",
            {"username": username,"password":h ,"name": name, "email":email})
            db.commit() 
            session["USERNAME"] = username           
            return render_template("homePage.html")

        except Exception as e:
            flash ("Can not create the user !")
            print(e)
            error = "Something is not right"
            return render_template("error.html", error=error)	

         
        

            
@app.route("/login", methods=["POST"])   
def userlogin():

    error = None
    #Validate the username and Password
    try:
        username = request.form.get("username")
        password = request.form.get("password")
        if username =='':
            error= 'Username can not be blank'
            return render_template("loginPage.html", error=error)
        elif password=='':
            error= 'Password can not be blank'
            return render_template("loginPage.html", error=error)
        else:
            print(username)
            quarydata = db.execute("SELECT * FROM users WHERE username =:username",{"username": username}).fetchall()
            print(quarydata)
            pass1= quarydata[0][2]
            user =quarydata[0][1]
            print(pass1)
            userid= quarydata[0][0]
            print(userid)
            if quarydata is None:
                error = "Invalid credentials 13, try again."
                return render_template("loginPage.html", error=error)

            elif sha256_crypt.verify(password,pass1):
                db.execute("INSERT INTO userlogin(user_id) VALUES (:user_id)",
                {"user_id": userid})
                db.commit()
                session["USERNAME"] = username
                print(session)
                return render_template("homePage.html", username= username)
            else:
                error = "Invalid credentials, try again."
                return render_template("loginPage.html", error=error)
         

    except Exception as e:
        print(e)
        error = "Invalid credentials, try again."
        return render_template("loginPage.html", error=error)
         
@app.route("/search", methods=["POST"])
def search():
    try:
        qvalue = request.form.get('qvalue')
        print(qvalue)
        search = '%' + qvalue + '%'
        quarydata = db.execute(("SELECT * FROM books WHERE title LIKE (:qvalue)"
        " OR isbn LIKE (:qvalue) OR author LIKE (:qvalue) ORDER BY isbn ASC LIMIT 10 "), {'qvalue': search})
        data = quarydata.fetchall()
        print(data)
        return render_template('resultsPage.html', results= data)
    except Exception as e:
        print(e)
        error = "Something is not right"
        return render_template("error.html", error=error)		


@app.route('/books/<string:isbn>')
def books(isbn):
    try:
        r_count=review_counts(isbn)
        if r_count =='Response [404]':
         print(error)
         return render_template('bookPage.html', error=error)

    except Exception as e:
        error = "ISBN is Invalid"
        print(error)
        return render_template('error.html', error=error)
    quarydata = db.execute('SELECT * FROM books WHERE isbn = (:isbn)',
            {'isbn': isbn}).fetchall()
    reviewquery = db.execute(('SELECT r.review, r.rating, r.review_date, u.username'
    ' FROM reviews AS r JOIN users AS u ON r.userid=u.userid '
    'WHERE r.book_id = (:isbn)')
    , {'isbn': isbn})
    reviews = reviewquery.fetchall()
    username = session.get('USERNAME')
    print(username)
    reviewedquery = db.execute('SELECT review FROM reviews'
        ' WHERE book_id = (:isbn) AND userid = (SELECT userid FROM users '
        'WHERE username =(:username))',
         {'username': username, 'isbn': isbn}).fetchall()
    REVIEWED_FLAG = False
    if reviewedquery:
        REVIEWED_FLAG = True

    return render_template('booksPage.html', book=quarydata[0], reviews=reviews,
            reviewed=REVIEWED_FLAG,  review_nums=review_counts(isbn))
            #review_nums=review_counts(isbn))

@app.route('/review', methods=['GET', 'POST'])
def review():
    title = request.args.get('title', None)
    author = request.args.get('author', None)
    if request.method == 'POST':
        username = session.get('USERNAME')
        isbn = request.args.get('isbn', None)
        text = request.form.get('review')
        rating = request.form.get('rate')
        today = datetime.today()
        query= db.execute('SELECT userid FROM users WHERE username = (:username)',
            {'username': username}).fetchone()

        userid = query[0]
        print(userid)
        db.execute(('INSERT INTO reviews (review, rating, review_date,'
            ' book_id, userid) VALUES (:text, :rating, :today, :isbn,'
            ' :userid)'), {'text': text, 'rating': rating, 'today': today,
                'isbn': isbn, 'userid': userid})
        db.commit()
        flash('Review posted for {}'.format(title))
       # return redirect(url_for('books', isbn=isbn))
    return render_template('reviewPage.html', title=title, author=author)


def review_counts(isbn):
    url = 'https://www.goodreads.com/book/review_counts.json'
    try:
        res = requests.get(url, params={"key": "GW0T0AAuRKRUVFIECnzXQ", "isbns": isbn})
        print(res)    
        return res.json()['books'][0]
    except Exception as e:
        flash ("ISBN not found")
        return e
        
   
    
 

@app.route('/api/<isbn>')
def api(isbn):
    data = db.execute(('SELECT title, author, year FROM books'
        ' WHERE isbn = (:isbn)'), {'isbn': isbn}).fetchall()
    if not data:
        return jsonify({'error': 'Not found'}), 404
    d = review_counts(isbn)
    return jsonify(title=data[0][0], author=data[0][1], year=data[0][2],
            review_count=d['reviews_count'], average_score=d['average_rating'])




@app.route("/index")
def logout():
    session.clear()
    flash('You have successfully logged out.')
    print(session)
    return render_template("indexPage.html")


@app.route("/")
def index():
    return  render_template("indexPage.html")

@app.route("/login")
def login():
   
    return render_template("loginPage.html")

@app.route("/register")
def register():
   
    return render_template("register.html")

@app.route("/home")
def home():
   
    return render_template("homePage.html")

if __name__ == "__main__":
  app.run(debug=True)
