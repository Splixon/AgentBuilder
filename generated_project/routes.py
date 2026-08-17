from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List

from . import crud, models, schemas
from .database import SessionLocal

router = APIRouter()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# User Authentication
@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = crud.get_user_by_username(db=next(get_db()), username=form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if not crud.verify_password(plain_password=form_data.password, hashed_password=user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {
        "access_token": user.username,
        "token_type": "bearer"
    }

@router.post("/signup")
async def signup(user: schemas.UserCreate):
    db = next(get_db())
    if crud.get_user_by_username(db=db, username=user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    crud.create_user(db=db, user=user)
    return {
        "message": "User created successfully"
    }

# Blog Post Endpoints
@router.post("/blog-posts")
async def create_blog_post(blog_post: schemas.BlogPostCreate, db: Session = Depends(get_db)):
    return crud.create_blog_post(db=db, blog_post=blog_post)

@router.get("/blog-posts")
async def get_blog_posts(db: Session = Depends(get_db)):
    return crud.get_blog_posts(db=db)

@router.get("/blog-posts/{blog_post_id}")
async def get_blog_post(blog_post_id: int, db: Session = Depends(get_db)):
    blog_post = crud.get_blog_post(db=db, blog_post_id=blog_post_id)
    if not blog_post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return blog_post

@router.put("/blog-posts/{blog_post_id}")
async def update_blog_post(blog_post_id: int, blog_post: schemas.BlogPostUpdate, db: Session = Depends(get_db)):
    return crud.update_blog_post(db=db, blog_post_id=blog_post_id, blog_post=blog_post)

@router.delete("/blog-posts/{blog_post_id}")
async def delete_blog_post(blog_post_id: int, db: Session = Depends(get_db)):
    crud.delete_blog_post(db=db, blog_post_id=blog_post_id)
    return {
        "message": "Blog post deleted successfully"
    }

# URL Shortener Endpoints
@router.post("/shorten")
def shorten_url(url: str, db: Session = Depends(get_db)):
    short_url = crud.shorten_url(db=db, url=url)
    return {
        "short_url": short_url
    }

@router.get("/{short_url}")
def redirect_url(short_url: str, db: Session = Depends(get_db)):
    original_url = crud.redirect_url(db=db, short_url=short_url)
    if not original_url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return {
        "original_url": original_url
    }
