"""
Routes and views for the flask application.
"""

from datetime import datetime, timedelta

from flask import current_app as deadline_app
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user

from app.forms import (
    LoginForm,
    RegistrationForm,
    AssignmentForm,
    ClassForm,
    SubmissionForm,
    EnrollClassForm,
)
from app.models import User, Assignment, Class, Submission
from app import db


# ---------- HOME ----------

@deadline_app.route('/')
def home():
    """Render the home page."""
    return render_template(
        'index.html',
        title='Deadline',
        now=datetime.now(),
    )


# ---------- HELPER: GET CLASS IDS FOR CURRENT USER ----------

def _get_user_class_ids():
    """Return a set of class IDs the current user owns or is enrolled in."""
    owned_classes = Class.query.filter_by(owner_id=current_user.id).all()
    member_classes = current_user.classes.all()  # many-to-many backref

    class_ids = {c.id for c in owned_classes + member_classes}
    return class_ids


# ---------- TIMELINE / DEADLINES ----------

@deadline_app.route('/timeline')
@login_required
def timeline():
    """Show assignments for the current user ordered by due date."""
    class_ids = _get_user_class_ids()

    if class_ids:
        assignments = (
            Assignment.query
            .filter(Assignment.class_id.in_(class_ids))
            .order_by(Assignment.due_date)
            .all()
        )
    else:
        assignments = []

    return render_template(
        'timeline.html',
        title='Timeline',
        assignments=assignments,
        now=datetime.now(),
    )


@deadline_app.route('/deadlines')
@login_required
def deadlines():
    """Render upcoming deadlines for the current user."""
    class_ids = _get_user_class_ids()

    if class_ids:
        assignments = (
            Assignment.query
            .filter(Assignment.class_id.in_(class_ids))
            .order_by(Assignment.due_date)
            .all()
        )
    else:
        assignments = []

    return render_template(
        'deadlines.html',
        title='DeadLines',
        assignments=assignments,
        now=datetime.now(),
    )


# ---------- CLASSES ----------

@deadline_app.route('/classes')
@login_required
def classes():
    """Show classes the user owns and is enrolled in."""
    owned_classes = Class.query.filter_by(owner_id=current_user.id).all()
    enrolled_classes = current_user.classes.all()  # via backref

    return render_template(
        'classes.html',
        owned_classes=owned_classes,
        enrolled_classes=enrolled_classes,
    )


@deadline_app.route('/classes/new', methods=['GET', 'POST'])
@login_required
def new_class():
    """Create a new class."""
    form = ClassForm()
    if form.validate_on_submit():
        clazz = Class(
            name=form.name.data,
            description=form.description.data,
            owner=current_user,
        )
        # Owner is also a member of the class
        clazz.members.append(current_user)

        db.session.add(clazz)
        db.session.commit()
        flash('Class created!')
        return redirect(url_for('classes'))

    return render_template('class_form.html', form=form)


@deadline_app.route('/classes/enroll', methods=['GET', 'POST'])
@login_required
def enroll_in_class():
    """Enroll in an existing class"""
    form = EnrollClassForm()
    if form.validate_on_submit():

        """check if the class code exists in the database at all"""
        if Class.query.filter_by(id=form.classCode.data).first() is None:
            flash('Invalid Class Code')
            return redirect(url_for('enroll_in_class'))
        """check if user is already a member of this class"""

        clazz = Class.query.get_or_404(form.classCode.data)
        if current_user == clazz.owner or clazz.members.filter_by(id=current_user.id).first():
            flash('Already Enrolled')
            return redirect(url_for('enroll_in_class'))
        
        clazz.members.append(current_user)
        db.session.commit()
        flash('Enrolled in Class!')
        return redirect(url_for('classes'))

    return render_template('class_enroll_form.html', form=form, title="Classes")



@deadline_app.route('/classes/<int:class_id>')
@login_required
def class_detail(class_id):
    """View a single class and its assignments."""
    clazz = Class.query.get_or_404(class_id)

    # Only owner or enrolled members can view
    if current_user != clazz.owner and not clazz.members.filter_by(
        id=current_user.id
    ).first():
        abort(403)

    assignments = (
        Assignment.query
        .filter_by(class_id=clazz.id)
        .order_by(Assignment.due_date)
        .all()
    )

    return render_template('class_detail.html', clazz=clazz, assignments=assignments)


# ---------- ASSIGNMENTS (CREATE INSIDE CLASS, LIST ALL) ----------

@deadline_app.route('/classes/<int:class_id>/assignments/new', methods=['GET', 'POST'])
@login_required
def new_assignment(class_id):
    """Create a new assignment inside a specific class."""
    clazz = Class.query.get_or_404(class_id)

    # Only the class owner can create assignments
    if current_user != clazz.owner:
        abort(403)

    form = AssignmentForm()
    if form.validate_on_submit():
        assignment = Assignment(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            clazz=clazz,
            creator=current_user,
        )
        db.session.add(assignment)
        db.session.commit()
        flash('Assignment created!')
        return redirect(url_for('class_detail', class_id=clazz.id))

    return render_template('assignment_form.html', form=form, clazz=clazz)


@deadline_app.route('/assignments')
@login_required
def assignments():
    """List assignments in classes the current user belongs to."""
    class_ids = _get_user_class_ids()

    if class_ids:
        assignments_list = (
            Assignment.query
            .filter(Assignment.class_id.in_(class_ids))
            .order_by(Assignment.due_date)
            .all()
        )
    else:
        assignments_list = []

    return render_template(
        'assignments.html',
        title='Assignments',
        assignments=assignments_list,
    )


# ---------- SUBMISSIONS (PER-STUDENT WORK) ----------

@deadline_app.route('/assignments/<int:assignment_id>/submit', methods=['GET', 'POST'])
@login_required
def submit_assignment(assignment_id):
    """Create or edit the current user's submission for an assignment."""
    assignment = Assignment.query.get_or_404(assignment_id)
    clazz = assignment.clazz

    # Must be in the class (or be the owner)
    if current_user != clazz.owner and not clazz.members.filter_by(
        id=current_user.id
    ).first():
        abort(403)

    form = SubmissionForm()

    # If they already submitted, load it so they can edit
    submission = Submission.query.filter_by(
        assignment_id=assignment.id,
        student_id=current_user.id,
    ).first()

    if form.validate_on_submit():
        if submission is None:
            submission = Submission(
                assignment=assignment,
                student=current_user,
            )
            db.session.add(submission)

        submission.content = form.content.data
        submission.submitted_at = datetime.utcnow()
        db.session.commit()
        flash('Your work has been submitted.')
        return redirect(url_for('class_detail', class_id=clazz.id))

    # Pre-fill with existing content if any
    if request.method == 'GET' and submission:
        form.content.data = submission.content

    return render_template('submit_assignment.html', form=form, assignment=assignment)


@deadline_app.route('/assignments/<int:assignment_id>/submissions')
@login_required
def view_submissions(assignment_id):
    """Teacher view of all submissions for an assignment."""
    assignment = Assignment.query.get_or_404(assignment_id)
    clazz = assignment.clazz

    if current_user != clazz.owner:
        abort(403)

    submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
    return render_template(
        'submissions.html',
        assignment=assignment,
        submissions=submissions,
    )


# ---------- AUTH ROUTES ----------

@deadline_app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with form + logic."""
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
    """Log the user out."""
    logout_user()
    return redirect(url_for('home'))


@deadline_app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form)
