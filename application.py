import os
import requests
import re
from datetime import datetime
from passlib.hash import sha256_crypt
from flask import request, jsonify, redirect
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
    elif len(password)<=3:
         error= 'Password can not be less than 4 charactor'
         return render_template("register.html", error=error)
    elif password == username or password == name:
         error= 'Username or Name can not be use as password'
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
            return render_template("homePage.html", username= username)

        except Exception as e:
            flash ("Can not create the user !")
            print(e)
            error = "Something is not right"
            return render_template("error.html", error=error)	

         
        

            
@app.route("/home", methods=["POST"])   
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
          
            quarydata = db.execute("SELECT * FROM users WHERE username =:username",{"username": username}).fetchall()
            
            pass1= quarydata[0][2]
            user =quarydata[0][1]
         
            userid= quarydata[0][0]
            
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
    username = session.get('USERNAME')
    if username is None:
        return render_template("loginPage.html")
    else:
        try:
            qvalue = request.form.get('qvalue')
            print(qvalue)
            search = '%' + qvalue + '%'
            quarydata = db.execute(("SELECT * FROM books WHERE title LIKE (:qvalue)"
            " OR isbn LIKE (:qvalue) OR author LIKE (:qvalue) ORDER BY isbn ASC LIMIT 10 "), {'qvalue': search})
            data = quarydata.fetchall()
            countdata= db.execute(("SELECT COUNT(*) FROM books WHERE title LIKE (:qvalue)"
            " OR isbn LIKE (:qvalue) OR author LIKE (:qvalue) "), {'qvalue': search}).fetchall()
        
            print(data)
       
            quarycount=countdata[0][0]
            print(quarycount)
            return render_template('resultsPage.html', results= data, username= username,quarycount=quarycount)
        except Exception as e:
            print(e)
            error = "Something is not right"
            return render_template("error.html", error=error)		


@app.route('/books/<string:isbn>')
def books(isbn):
    username = session.get('USERNAME')
    if username ==None:
        print(username)
        return render_template("loginPage.html")
    else:
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
   
        print('still books')
        print(username)
        reviewedquery = db.execute('SELECT review FROM reviews'
            ' WHERE book_id = (:isbn) AND userid = (SELECT userid FROM users '
            'WHERE username =(:username))',
            {'username': username, 'isbn': isbn}).fetchall()
        reviwed_flag = False
        if reviewedquery:
            reviwed_flag = True

        return render_template('booksPage.html', book=quarydata[0], reviews=reviews,
            reviewed=REVIEWED_FLAG,  review_nums=review_counts(isbn),username=username)
           

@app.route('/books/<string:isbn>', methods=["POST"])
def review(isbn):
    title = request.args.get('title', None)
    author = request.args.get('author', None)
    username = session.get('USERNAME')
    print(username)
    if username ==None:
        print(username)
        return render_template("loginPage.html")
    else:    
        text = request.form.get('review')
        rating = request.form.get('rate')
        today = datetime.today()
        query= db.execute('SELECT userid FROM users WHERE username = (:username)',
            {'username': username}).fetchone()

        userid = query[0]
        print('hello')
        print(isbn)
        print(userid)
        if rating is None:
            rating=0
        try:
            db.execute(('INSERT INTO reviews (review, rating, review_date,'
                ' book_id, userid) VALUES (:text, :rating, :today, :isbn,'
                ' :userid)'), {'text': text, 'rating': rating, 'today': today,
                'isbn': isbn, 'userid': userid})
            db.commit()
            print('done')
            return redirect(request.referrer)
        except Exception as e:
            flash('Review posted for {}'.format(title))
            print(e)
            error ="Something went wrong with saving your review please refresh the page"
            return render_template('error.html', error=error)
        
        


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
    username= session.get("USERNAME")
    if username is None:
        return render_template("loginPage.html")
    else:
        return render_template("homePage.html", username= username)


@app.route("/updateprofile")
def update():
    username= session.get("USERNAME")
    if username is None:
        return render_template("loginPage.html")
    else:
        
        try:
            query= db.execute("SELECT email,name FROM  users WHERE username=(:username)",{"username": username}).fetchall()
            name = query[0][1]
            email = query[0][0]
            return render_template('profilePage.html', email=email , name= name, username=username )
        except Exception as e:
            print(e)
            error ="Something went wrong with saving your review please refresh the page"
            return render_template('error.html', error=error)


@app.route("/updateprofile", methods=["POST"])
def userupdate():
    username= session.get("USERNAME")
    name=request.form.get("name")
    password= request.form.get("password")
    confirmPassword=request.form.get("confirmPassword")
    email = request.form.get("email")
    h = sha256_crypt.encrypt(password)
    error =None
    string_check= re.compile('%&') 
    try:
        if password =='' and email=='':
            ererror= 'Nothing to update'
            return render_template("profilePage.html", error=error)
        elif email!='' and password=='':
           db.execute("UPDATE users SET email=(:email) WHERE username=:username)",{'email':email,'username':username})
           db.commit()
           error="Email updated"
           return render_template("profilePage.html", error=error)
        
        elif password == username or password == name:
            error= 'Username or Name can not be use as password'
            return render_template("profilePage.html", error=error)
        elif string_check.search(password) != None:
            error ='Password not allow &, %, /'
            return render_template("profilePage.html", error=error)
        elif password != confirmPassword:
            error= 'Password is not match with the Confirm Password'
            return redirect(request.referrer, error=error)
        elif len(password)<=4:
            error= 'Password can not be less than 4 charactor'
            return render_template("profilePage.html", error=error)
       
        elif email =='' and password!='':
            db.execute(("UPDATE users SET password=(:password) WHERE username=:username"),{'password':h,'username':username})
            db.commit()
            error="Password  updated"
            return render_template("profilePage.html", error=error)
        else:
            db.execute(("UPDATE users SET password=(:password), email=(:email) WHERE username=:username"),{'password':h,'email':email,'username':username})
            db.commit()
            error="Password and Email updated"
            return render_template("profilePage.html", error=error)
    except Exception as e:
        error=e
        return render_template("profilePage.html", error=error)




if __name__ == "__main__" :
  app.run(debug=True)
