from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

#users enrolled in classes
class_memberships = db.Table(
    'class_memberships',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('class_id', db.Integer, db.ForeignKey('class.id'), primary_key=True),
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(128), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    notifications_enabled = db.Column(db.Boolean, default=True)

    def set_password(self, password):
            self.password_hash = generate_password_hash(
            password,
            method="pbkdf2:sha256"
        )

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
    
#added for class assignemnt connection
class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', backref='owned_classes')

    # students (and owner) enrolled in this class
    members = db.relationship(
        'User',
        secondary=class_memberships,
        backref=db.backref('classes', lazy='dynamic'),
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<Class {self.name}>'


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reminder_hours = db.Column(db.Integer, default=24)
  # who created the assignment
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    creator = db.relationship('User', backref='created_assignments')

    # which class this assignment belongs to
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    clazz = db.relationship('Class', backref='assignments')

    def __repr__(self):
        return f'<Assignment {self.title}>'
    
class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    content = db.Column(db.Text)  # or a file path / URL if you want uploads
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    assignment = db.relationship('Assignment', backref='submissions')
    student = db.relationship('User', backref='submissions')

    __table_args__ = (
        db.UniqueConstraint('assignment_id', 'student_id', name='uq_assignment_student'),
    )

    def __repr__(self):
        return f'<Submission assignment={self.assignment_id} student={self.student_id}>'
