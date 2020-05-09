import os 
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def create_tables():
    """Creates books, users, userlogin, and  boolreviews tables"""
    commands = (
        
        ('CREATE TABLE books ('
            'isbn VARCHAR PRIMARY KEY, '
            'title VARCHAR NOT NULL, '
            'author VARCHAR NOT NULL, '
            'year INT NOT NULL)'),
        ('CREATE TABLE users ('
            'userid SERIAL PRIMARY KEY, '
            'email VARCHAR NOT NULL, '
            'password VARCHAR NOT NULL, '
            'name VARCHAR(20) NOT NULL, '
            'username VARCHAR(20) UNIQUE NOT NULL)'),
        ('CREATE TABLE userlogin ('
            'loginid SERIAL PRIMARY KEY,' 
            'user_id  INT NOT NULL,  FOREIGN KEY(user_id) REFERENCES users(userid),'
            'logintime TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'),
        ('CREATE TABLE reviews ('
            'review_id SERIAL PRIMARY KEY, '
            'review VARCHAR NOT NULL, '
            'rating SMALLINT NOT NULL, '
            'review_date DATE NOT NULL, '
            'book_id VARCHAR NOT NULL, FOREIGN KEY(book_id) REFERENCES books(isbn),'
            'userid INT NOT NULL)')
        )
    for command in commands:
        db.execute(command)
    db.commit()

if __name__ == '__main__':
    create_tables()