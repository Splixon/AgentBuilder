from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

engine = create_engine('sqlite:///database.db')
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String)
    email = Column(String)

class BlogPost(Base):
    __tablename__ = 'blog_posts'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User')
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

def create_user(username, email):
    user = User(username=username, email=email)
    session.add(user)
    session.commit()
    return user

def get_user(id):
    return session.query(User).filter_by(id=id).first()

def create_blog_post(title, content, user_id):
    blog_post = BlogPost(title=title, content=content, user_id=user_id)
    session.add(blog_post)
    session.commit()
    return blog_post

def get_blog_post(id):
    return session.query(BlogPost).filter_by(id=id).first()

def update_blog_post(id, title, content):
    blog_post = get_blog_post(id)
    if blog_post:
        blog_post.title = title
        blog_post.content = content
        session.commit()
    return blog_post

def delete_blog_post(id):
    blog_post = get_blog_post(id)
    if blog_post:
        session.delete(blog_post)
        session.commit()
    return blog_post
