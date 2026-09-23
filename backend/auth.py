"""Local demonstration identity; no sign-in or password is required."""
from fastapi import HTTPException, Request
from .db import Session, User, Audit

LOCAL_USER = {'id':'admin','name':'Local workspace','role':'admin'}

def init_users(s):
    user=s.get(User,'admin')
    if not user:s.add(User(id='admin',role='admin',name='Local workspace',password_hash=''))
    else:user.name='Local workspace';user.password_hash=''
    operator=s.get(User,'operator')
    if operator:operator.password_hash=''

def current_user(request: Request):
    return dict(LOCAL_USER)

def admin_user(request: Request):
    user=current_user(request)
    if user['role']!='admin':raise HTTPException(403,'Administrator access is required.')
    return user

def audit(s,user,action,target,details=None):
    s.add(Audit(actor=user['id'],action=action,target=str(target),details=details or {}))
