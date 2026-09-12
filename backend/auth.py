import hashlib, hmac, os, secrets, time
from fastapi import HTTPException, Request
from .db import Session, User, LoginSession, Audit

def hash_password(password):
    salt=secrets.token_hex(16)
    digest=hashlib.scrypt(password.encode(),salt=salt.encode(),n=16384,r=8,p=1).hex()
    return salt+':'+digest
def verify_password(password,encoded):
    salt,digest=encoded.split(':')
    actual=hashlib.scrypt(password.encode(),salt=salt.encode(),n=16384,r=8,p=1).hex()
    return hmac.compare_digest(digest,actual)
def init_users(s):
    for username,role,name in [('admin','admin','Demo administrator'),('operator','operator','Delhi operator')]:
        if not s.get(User,username):
            s.add(User(id=username,role=role,name=name,password_hash=hash_password(os.environ['SYLRAK_'+username.upper()+'_PASSWORD'])))
def current_user(request: Request):
    token=request.cookies.get('sylrak_session','')
    with Session() as s:
        login=s.get(LoginSession,hashlib.sha256(token.encode()).hexdigest())
        if not login or login.expires_at<time.time(): raise HTTPException(401,'Sign in to continue.')
        user=s.get(User,login.user_id)
        return {'id':user.id,'name':user.name,'role':user.role}
def admin_user(request: Request):
    user=current_user(request)
    if user['role']!='admin': raise HTTPException(403,'Administrator access is required.')
    return user
def audit(s,user,action,target,details=None):
    s.add(Audit(actor=user['id'],action=action,target=str(target),details=details or {}))
