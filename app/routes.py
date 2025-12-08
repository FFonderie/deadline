"""
Routes and views for the flask application.
"""

from datetime import datetime

from flask import render_template, redirect, url_for, flash, request
from flask import current_app as deadline_app
from flask_login import login_user, logout_user, login_required, current_user

from app.forms import LoginForm, RegistrationForm, AssignmentForm
from app.models import User, Assignment
from app import db

#for timeline
from flask_login import login_required, current_user
from app.models import Assignment


@deadline_app.route('/')
def home():
    """renders the home page"""
    return render_template(
        'index.html',
        title='Deadline',
        year=datetime.now().year,
    )



#requires login, grabs only user's assignments, pass them onto template called assignments
@deadline_app.route('/timeline')
@login_required
def timeline():
    """Show assignments for the current user ordered by due date."""
    assignments = (
        Assignment.query
        .filter_by(user_id=current_user.id)
        .order_by(Assignment.due_date)
        .all()
    )
    return render_template(
        'timeline.html',
        title='Timeline',
        assignments=assignments,
    )


@deadline_app.route('/classes')
def classes():
    """renders a classes page"""
    return render_template(
        'classes.html',
        title='Classes',
    )


@deadline_app.route('/deadlines')
def deadlines():
    """renders a deadlines page"""
    return render_template(
        'deadlines.html',
        title='DeadLines',
    )


# ---------- AUTH ROUTES ----------

@deadline_app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with form + logic"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('home'))

    return render_template('login.html', title='Sign In', form=form)


@deadline_app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@deadline_app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form)


# ---------- ASSIGNMENT ROUTES (CRUD) ----------

@deadline_app.route('/assignments', methods=['GET', 'POST'])
@login_required
def assignments():
    form = AssignmentForm()
    if form.validate_on_submit():
        assignment = Assignment(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            user=current_user   # <-- THIS is important
        )
        db.session.add(assignment)
        db.session.commit()
        flash('Assignment created!')
        return redirect(url_for('assignments'))

    assignments_list = Assignment.query.filter_by(user_id=current_user.id).all()
    return render_template(
        'assignments.html',
        title='Assignments',
        form=form,
        assignments=assignments_list
    )
