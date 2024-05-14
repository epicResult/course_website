from flask import Flask, render_template, request, flash, redirect, url_for, session
from datetime import timedelta
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy


# initialize flask
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config["SECRET_KEY"] = (
    "8a0f946f1471e113e528d927220ad977ed8b2cce63303beff10c8cb4a15e1a99"
)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///course.db"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=10)

# intitalize db
db = SQLAlchemy(app)


# this function parses a raw date string into a more presentable format
def parse_date(date: str) -> str:
    return date[:10] + ", " + date[11:]


# add the parse data function to jinja2 template
app.jinja_env.globals.update(parse_date=parse_date)


# database response class
class DBResponse:
    def __init__(self, success, message):
        self.success = success
        self.message = message

    def to_dict(self):
        return {"success": self.success, "message": self.message}


# tables
class Person(db.Model):
    __tablename__ = "Person"

    username = db.Column(db.String(20), primary_key=True)
    last_name = db.Column(db.String(20), nullable=False)
    first_name = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(20), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f"Person('{self.username}', '{self.first_name}')"


class Grades(db.Model):
    __tablename__ = "Grades"

    student_username = db.Column(
        db.String(20), db.ForeignKey("Person.username"), primary_key=True
    )
    assessment_name = db.Column(
        db.String(30), db.ForeignKey("Assessments.assessment_name"), primary_key=True
    )
    assessment_type = db.Column(db.String(20), nullable=False)
    grade = db.Column(db.Integer, default=None)


class Regrades(db.Model):
    __tablename__ = "Regrades"

    regrade_id = db.Column(db.Integer, primary_key=True)
    assessment_name = db.Column(
        db.String(30), db.ForeignKey("Assessments.assessment_name"), nullable=False
    )
    student_username = db.Column(
        db.String(20), db.ForeignKey("Person.username"), nullable=False
    )
    description = db.Column(db.String(1000), nullable=False)
    status = db.Column(db.Boolean, default=False, nullable=False)


class Assessments(db.Model):

    __tablename__ = "Assessments"

    assessment_name = db.Column(db.String(30), primary_key=True)
    assessment_type = db.Column(db.String(20), nullable=False)
    due_date = db.Column(db.String(20))
    location = db.Column(db.String(20))
    weight = db.Column(db.REAL)
    handout_link = db.Column(db.String(100))
    solutions_link = db.Column(db.String(100))
    description = db.Column(db.String(1000), nullable=False)


class Feedback(db.Model):

    __tablename__ = "Feedback"

    id = db.Column(db.Integer, primary_key=True)
    instructor_username = db.Column(
        db.String(20), db.ForeignKey("Person.username"), nullable=False
    )
    instructor_like = db.Column(db.String(1000))
    instructor_improve = db.Column(db.String(1000))
    labs_like = db.Column(db.String(1000))
    labs_improve = db.Column(db.String(1000))


# HELPER FUNCTIONS


# this function queries grades and returns them as a dict, where keys are assessments
def make_grades_dict():
    all_grades = Grades.query.order_by(Grades.assessment_type.asc())

    grades_by_assessment = {}
    grades_avg = {}
    grades_count = {}

    for grade in all_grades:
        if grade.assessment_name not in grades_by_assessment:
            grades_by_assessment[grade.assessment_name] = [grade]
            grades_avg[grade.assessment_name] = grade.grade
            grades_count[grade.assessment_name] = 1
        else:
            grades_by_assessment[grade.assessment_name].append(grade)
            grades_avg[grade.assessment_name] += grade.grade
            grades_count[grade.assessment_name] += 1

    for assessment in grades_avg:
        grades_avg[assessment] = round(
            grades_avg[assessment] / grades_count[assessment], 2
        )

    return grades_by_assessment, grades_avg


# like the previous function but for regrades
def make_regrades_dict():
    all_regrades = Regrades.query.filter(Regrades.status == 0)

    regrades_by_assessment = {}
    # grades_avg = {}
    regrades_count = {}

    for regrade in all_regrades:
        if regrade.assessment_name not in regrades_by_assessment:
            regrades_by_assessment[regrade.assessment_name] = [regrade]
            regrades_count[regrade.assessment_name] = 1
        else:
            regrades_by_assessment[regrade.assessment_name].append(regrade)
            regrades_count[regrade.assessment_name] += 1

    return regrades_by_assessment


# calculates a students final grade given their grades db query tuple
def calculate_overall_mark(grades):
    total_weight = 0
    final_mark = 0
    mark = 0

    for grade in grades:
        mark += (grade.grade / 100) * grade.weight
        total_weight += grade.weight

    if total_weight == 0:
        return 0

    final_mark = round((mark / total_weight) * 100, 2)
    return final_mark


# resolves a regrade request in the db
def process_regrade(regrade_id, new_grade):

    # incomplete form
    if not new_grade:
        response = DBResponse(success=False, message="Please fill all the fields")
        return response.to_dict()

    # get the regrade request
    regrade_tuple = Regrades.query.filter_by(regrade_id=regrade_id).first()

    # get the grade tuple
    grade_tuple = Grades.query.filter_by(
        student_username=regrade_tuple.student_username,  # type: ignore
        assessment_name=regrade_tuple.assessment_name,  # type: ignore
    ).first()

    # update the data
    regrade_tuple.status = 1  # type: ignore
    grade_tuple.grade = new_grade  # type: ignore

    # update db
    try:
        db.session.commit()
        response = DBResponse(success=True, message="Regrade processed")

        return response.to_dict()

    except Exception as error:
        response = DBResponse(
            success=False, message=f"Database Error: {type(error).__name__}"
        )

        return response.to_dict()


# this function gets all the assignments
def query_assignments():
    assignments = Assessments.query.filter_by(assessment_type="assignment").all()
    return assignments


# this function gets all the assignments
def query_labs():
    labs = Assessments.query.filter_by(assessment_type="lab").all()
    return labs


# this function gets all the tests
def query_tests():
    tests = Assessments.query.filter_by(assessment_type="test").all()
    return tests


# this function checks if a given username is in the db
def check_username(username: str):
    user = Person.query.filter_by(username=username).first()
    return user


# this function checks if a given assessment is in the db
def check_assessment_name(name: str):
    assessment = Assessments.query.filter_by(assessment_name=name).first()
    return assessment


# this function checks if a given student's grade is in the db
def check_grade(assessment: str, student: str):
    grade = Grades.query.filter_by(
        assessment_name=assessment, student_username=student
    ).first()
    return grade


# this function checks if a given regrade request is in the db
def check_regrade(assessment: str, student: str):
    regrade = Regrades.query.filter_by(
        assessment_name=assessment, student_username=student, status=0
    ).first()
    return regrade


# this function adds an assingment to the db
def add_assignment(details) -> dict:
    name, due_date, weight, topic, handout, solution = details

    # form validations
    if details.count("") > 0:
        response = DBResponse(success=False, message="Please fill all the fields")
        return response.to_dict()

    if check_assessment_name(name):
        response = DBResponse(
            success=False, message="This assessment is already in use"
        )
        return response.to_dict()

    # all fields are non empty, and username and email are unique
    # so, create user

    assignment = Assessments(
        assessment_name=name,
        assessment_type="assignment",
        due_date=due_date,
        weight=weight,
        handout_link=handout,
        solutions_link=solution,
        description=topic,
    )  # type: ignore

    # add to db
    try:
        db.session.add(assignment)
        db.session.commit()

        response = DBResponse(success=True, message="Assignment added")

        return response.to_dict()
    except Exception as error:
        response = DBResponse(
            success=False, message=f"Database Error: {type(error).__name__}"
        )

        return response.to_dict()


# this function adds an assingment to the db
def add_lab(details) -> dict:
    name, topic, handout, solution = details

    # form validations
    if details.count("") > 0:
        response = DBResponse(
            success=False, message=f"Please fill all the fieldsaaaa {details}"
        )
        return response.to_dict()

    if check_assessment_name(name):
        response = DBResponse(
            success=False, message="This assessment is already in use"
        )
        return response.to_dict()

    # all fields are non empty, and username and email are unique
    # so, create user

    lab = Assessments(
        assessment_name=name,
        assessment_type="lab",
        handout_link=handout,
        solutions_link=solution,
        description=topic,
        weight=0.2,
    )  # type: ignore

    # add to db
    try:
        db.session.add(lab)
        db.session.commit()

        response = DBResponse(success=True, message="Lab added")

        return response.to_dict()
    except Exception as error:
        response = DBResponse(
            success=False, message=f"Database Error: {type(error).__name__}"
        )

        return response.to_dict()


# this function inserts a regrade req in the db
def insert_regrade(details) -> dict:
    assessment_name, student, description = details

    # form validation
    if details.count("") > 0:
        response = DBResponse(
            success=False, message=f"Please fill all the fields {details}"
        )
        return response.to_dict()

    if check_regrade(assessment_name, student):
        response = DBResponse(
            success=False,
            message="You have already have an active regrade request for this assessment. Please reach out to an instructor for any further concerns",
        )
        return response.to_dict()

    # all fields are non empty, and username and email are unique
    # so, create user

    regrade = Regrades(
        assessment_name=assessment_name,
        student_username=student,
        description=description,
        status=False,
    )  # type: ignore

    # add to db
    try:
        db.session.add(regrade)
        db.session.commit()

        response = DBResponse(success=True, message="Regrade added")

        return response.to_dict()
    except Exception as error:
        response = DBResponse(
            success=False, message=f"Database Error: {type(error).__name__}"
        )

        return response.to_dict()


# this function inserts a new feedback in the db
def submit_feedback(details) -> dict:
    # deconstruct the details tuple
    (
        instructor_username,
        like_instructor,
        improve_instructor,
        like_labs,
        improve_labs,
    ) = details

    # form validation
    if details.count("") > 0:
        response = DBResponse(success=False, message=f"Please answer all the questions")
        return response.to_dict()

    # all fields are non empty, and username and email are unique
    # so, create user

    # create new feedback
    feedback = Feedback(
        instructor_username=instructor_username,
        instructor_like=like_instructor,
        instructor_improve=improve_instructor,
        labs_like=like_labs,
        labs_improve=improve_labs,
    )  # type: ignore

    # insert to db
    try:
        db.session.add(feedback)
        db.session.commit()

        response = DBResponse(success=True, message="Feedback added")

        return response.to_dict()
    except Exception as error:
        response = DBResponse(
            success=False, message=f"Database Error: {type(error).__name__}"
        )

        return response.to_dict()


# this function inserts a grade in the db
def insert_grade(details) -> dict:
    assessment_name, assessment_type, student_name, grade = details

    # form validation
    if details.count("") > 0:
        response = DBResponse(
            success=False, message=f"Please fill all the fields {details}"
        )
        return response.to_dict()

    if check_grade(assessment_name, student_name):
        response = DBResponse(
            success=False,
            message="This student already has a grade for this assessment. You can update this grade via a regrade request",
        )
        return response.to_dict()

    user = check_username(student_name)

    if not user:
        response = DBResponse(
            success=False,
            message="This student does not exist in the database",
        )
        return response.to_dict()

    if user.user_type == "instructor":
        response = DBResponse(
            success=False,
            message="You can only add grades for students",
        )
        return response.to_dict()

    # all fields valid
    grade = Grades(
        assessment_name=assessment_name,
        assessment_type=assessment_type,
        student_username=student_name,
        grade=grade,
    )  # type: ignore

    # insert to db
    try:
        db.session.add(grade)
        db.session.commit()

        response = DBResponse(success=True, message="Grade added")

        return response.to_dict()
    except Exception as error:
        response = DBResponse(
            success=False, message=f"Database Error: {type(error).__name__}"
        )

        return response.to_dict()


# this function inserts an new test to the db
def add_test(details) -> dict:
    name, due_date, weight, location, content = details

    # form validation
    if details.count("") > 0:
        response = DBResponse(
            success=False, message=f"Please fill all the fields {details}"
        )
        return response.to_dict()

    if check_assessment_name(name):
        response = DBResponse(
            success=False, message="This assessment is already in use"
        )
        return response.to_dict()

    # all fields are valid

    test = Assessments(
        assessment_name=name,
        assessment_type="test",
        due_date=due_date,
        weight=weight,
        location=location,
        description=content,
    )  # type: ignore

    # insert to db
    try:
        db.session.add(test)
        db.session.commit()

        response = DBResponse(success=True, message="Test added")

        return response.to_dict()

    except Exception as error:
        response = DBResponse(
            success=False, message=f"Database Error: {type(error).__name__}"
        )

        return response.to_dict()


# this function adds a new user to the db
def add_users(reg_details) -> dict:
    username, first_name, last_name, password, user_type = reg_details

    # form validation
    if (
        username == ""
        or first_name == ""
        or last_name == ""
        or password == ""
        or user_type == ""
    ):
        response = DBResponse(success=False, message="Please fill all the fields")
        return response.to_dict()

    if check_username(username):
        response = DBResponse(success=False, message="This username is already in use")
        return response.to_dict()

    # all fields are non empty, and username and email are unique
    # so, create user

    user = Person(
        username=username,
        first_name=first_name,
        last_name=last_name,
        password=password,
        user_type=user_type,
    )  # type: ignore

    # add to db
    try:
        db.session.add(user)
        db.session.commit()

        response = DBResponse(
            success=True, message="Registration successful! Please login now"
        )

        return response.to_dict()
    except Exception as error:
        response = DBResponse(
            # success=False, message=f"Database Error: {type(error).__name__}"
            success=False,
            message=error,
        )

        return response.to_dict()


# these are the routes
# for each route, pagename is the name of the css file and title is the page title
# only home, login and register are viewable without login


@app.route("/")
@app.route("/home")
def home():
    pagename = "home"
    return render_template("home.html", pagename=pagename, title="CSCB20")


@app.route("/calendar")
def calendar():
    if "name" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html", pagename="login")

    return render_template("calendar.html", pagename="calendar", title="Calendar")


@app.route("/lectures")
def lectures():
    if "name" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html", pagename="login")
    pagename = "lectures"
    return render_template("lectures.html", pagename=pagename, title="Lectures")


@app.route("/labs")
def labs():
    if "name" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html", pagename="login")
    pagename = "labs"

    labs = query_labs()
    return render_template("labs.html", pagename=pagename, labs=labs, title="Labs")


@app.route("/assignments")
def assignments():
    if "name" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html", pagename="login")
    pagename = "assignments"

    # get all the assignments
    assignments = query_assignments()

    return render_template(
        "assignments.html",
        pagename=pagename,
        assignments=assignments,
        title="Assignments",
    )


@app.route("/news")
def news():
    if "name" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html", pagename="login")

    pagename = "news"

    return render_template("news.html", pagename=pagename, title="News")


@app.route("/tests")
def tests():
    if "name" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html", pagename="login")

    pagename = "tests"

    # get all the tests
    tests = query_tests()

    return render_template("tests.html", pagename=pagename, tests=tests, title="Tests")


@app.route("/resources")
def resources():
    if "name" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html", pagename="login")

    pagename = "resources"

    return render_template("resources.html", pagename=pagename, title="Resources")


@app.route("/user")
def user():
    if "name" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html", pagename="login")

    pagename = "user"

    # get current user
    person = Person.query.filter_by(username=session["name"]).first()

    return render_template(
        "user.html", pagename=pagename, user=person, title="My Account"
    )


@app.route("/course_team")
def course_team():
    if "name" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html", pagename="login")

    pagename = "course_team"

    return render_template("course_team.html", pagename=pagename, title="Course Team")


@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    pagename = "feedback"

    if "name" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html", pagename="login", title="Feedback")

    # frontend
    if request.method == "GET":
        if session["user_type"] == "student":

            # student view
            instructors = Person.query.filter_by(user_type="instructor").all()

            return render_template(
                "feedback.html",
                pagename=pagename,
                instructors=instructors,
                title="Feedback",
            )

        # instructor view
        else:
            # get all the feedback
            all_feedback = (
                Feedback.query.filter_by(instructor_username=session["name"])
                .order_by(Feedback.id.desc())
                .all()
            )

            return render_template(
                "feedback.html",
                pagename=pagename,
                all_feedback=all_feedback,
                title="Feedback",
            )

    else:
        # collect form data
        instructor_username = request.form["instructor_name"]
        like_instructor = request.form["like_instructor"]
        improve_instructor = request.form["improve_instructor"]
        like_labs = request.form["like_labs"]
        improve_labs = request.form["improve_labs"]

        feedback_tuple = (
            instructor_username,
            like_instructor,
            improve_instructor,
            like_labs,
            improve_labs,
        )
        response = submit_feedback(feedback_tuple)

        if not response["success"]:
            instructors = Person.query.filter_by(user_type="instructor").all()
            return render_template(
                "feedback.html",
                pagename=pagename,
                error=response["message"],
                title="Feedback",
                instructors=instructors,
            )

        flash("Feedback submitted!")

        return redirect(url_for("feedback"))


@app.route("/grades")
def grades():
    pagename = "grades"

    if "name" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html", pagename="login", title="Login")

    if session["user_type"] == "student":
        grades = (
            db.session.query(Grades.assessment_name, Grades.grade, Assessments.weight)
            .join(Assessments, Grades.assessment_name == Assessments.assessment_name)
            .filter(Grades.student_username == session["name"])
            .all()
        )

        final_mark = calculate_overall_mark(grades)

        return render_template(
            "grades.html",
            pagename=pagename,
            grades=grades,
            final_mark=final_mark,
            title="Grades",
        )
    else:
        grades = make_grades_dict()

        return render_template(
            "grades.html",
            pagename=pagename,
            grades=grades[0],
            avgs=grades[1],
            title="Grades",
        )


@app.route("/regrades")
def regrades():
    pagename = "regrades"
    title = "Regrades"

    if "name" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html", pagename="login", title="Login")

    # student view
    if session["user_type"] == "student":
        resolved_regrades = Grades.query.filter_by(
            student_username=session["name"]
        ).all()

        # query resolved regrades
        resolved_regrades = (
            db.session.query(
                Grades.assessment_name,
                Grades.grade,
                Assessments.weight,
                Regrades.description,
            )
            .join(Assessments, Grades.assessment_name == Assessments.assessment_name)
            .join(
                Regrades,
                (Grades.assessment_name == Regrades.assessment_name)
                & (Grades.student_username == Regrades.student_username),
            )
            .filter(
                (Grades.student_username == session["name"]) & (Regrades.status == 1)
            )
            .all()
        )

        # query resolved regrades
        unresolved_regrades = (
            db.session.query(
                Grades.assessment_name,
                Grades.grade,
                Assessments.weight,
                Regrades.description,
            )
            .join(Assessments, Grades.assessment_name == Assessments.assessment_name)
            .join(
                Regrades,
                (Grades.assessment_name == Regrades.assessment_name)
                & (Grades.student_username == Regrades.student_username),
            )
            .filter(
                (Grades.student_username == session["name"]) & (Regrades.status == 0)
            )
            .all()
        )

        return render_template(
            "regrades.html",
            pagename=pagename,
            resolved_regrades=resolved_regrades,
            unresolved_regrades=unresolved_regrades,
            title=title,
        )

    else:  # instructor view
        regrades = make_regrades_dict()

        return render_template(
            "regrades.html", pagename=pagename, regrades=regrades, title=title
        )


# route for each specific regrade request
@app.route("/regrade/<id>", methods=["GET", "POST"])
def regrade_id(id: int):
    pagename = "regrade_form"
    title = "Resolve Regrade"

    if "name" not in session:
        flash("You must be logged in as an instructor to view this page")
        return render_template("login.html", pagename="login", title="Login")

    # fetch the regrade request
    regrade_req = (
        db.session.query(
            Regrades.regrade_id,
            Regrades.assessment_name,
            Regrades.student_username,
            Regrades.description,
            Regrades.status,
            Grades.grade,
        )
        .join(
            Grades,
            db.and_(
                Regrades.student_username == Grades.student_username,
                Regrades.assessment_name == Grades.assessment_name,
            ),
        )
        .filter(Regrades.status == 0, Regrades.regrade_id == id)
        .first()
    )

    # frontent view
    if request.method == "GET":
        return render_template(
            "regrade_form.html", pagename=pagename, regrade_req=regrade_req, title=title
        )

    else:
        new_grade = request.form["new_grade"]

        response = process_regrade(id, new_grade)

        if not response["success"]:
            return render_template(
                "regrade_form.html",
                pagename=pagename,
                error=response["message"],
                regrade_req=regrade_req,
                title=title,
            )

        return redirect(url_for("regrades"))


@app.route("/register", methods=["GET", "POST"])
def register():
    title = "Register"

    if request.method == "GET":
        pagename = "register"

        return render_template("register.html", pagename=pagename, title=title)

    else:
        # get form data
        username = request.form["Username"]
        first_name = request.form["First_Name"]
        last_name = request.form["Last_Name"]
        user_type = request.form["User_type"]

        # try to hash
        try:
            hashed_password = bcrypt.generate_password_hash(
                request.form["Password"]
            ).decode("utf-8")
        except ValueError:
            # cannot hash, this would send an error the user after the add users function
            hashed_password = ""

        reg_details = (username, first_name, last_name, hashed_password, user_type)

        response = add_users(reg_details)

        if not response["success"]:
            flash("Error: " + response["message"])
            return render_template(
                "register.html",
                pagename="register",
                error=response["message"],
                title=title,
            )
        else:
            flash("Registration successful! Please login now:")
            return redirect(url_for("login"))


@app.route("/add_regrade", methods=["GET", "POST"])
def add_regrade():
    title = "Submit Regrade"
    if "name" not in session:
        return redirect(url_for("login"))

    # query assignments
    assessments = Grades.query.filter_by(student_username=session["name"])
    pagename = "add_regrade"

    if request.method == "GET":

        return render_template(
            "add_regrade.html", pagename=pagename, assessments=assessments, title=title
        )

    else:
        # get form data
        assessment_name = request.form["assessment_name"]
        student = session["name"]
        description = request.form["description"]

        regrade_tuple = (assessment_name, student, description)

        response = insert_regrade(regrade_tuple)

        if not response["success"]:
            return render_template(
                "add_regrade.html",
                pagename=pagename,
                assessments=assessments,
                error=response["message"],
                title=title,
            )

        flash("Regrade submitted!")

        return redirect(url_for("regrades"))


@app.route("/add_grade", methods=["GET", "POST"])
def add_grade():
    title = "Add Grade"
    pagename = "add_grade"

    # query students and assessments
    students = Person.query.filter_by(user_type="student").all()
    assessments = Assessments.query.all()

    if request.method == "GET":
        return render_template(
            "add_grade.html",
            pagename=pagename,
            students=students,
            assessments=assessments,
            title=title,
        )

    else:
        # get form data
        assessment_name = request.form["assessment_name"]
        student = request.form["student_name"]
        grade = request.form["grade"]
        assessment_type = ""

        # set assessment type
        for assessment in assessments:
            if assessment.assessment_name == assessment_name:
                assessment_type = assessment.assessment_type

        grade_tuple = (assessment_name, assessment_type, student, grade)

        response = insert_grade(grade_tuple)

        if not response["success"]:
            return render_template(
                "add_grade.html",
                pagename=pagename,
                students=students,
                assessments=assessments,
                error=response["message"],
                title=title,
            )

        flash("Grade added!")
        return render_template(
            "add_grade.html",
            pagename=pagename,
            students=students,
            assessments=assessments,
            title=title,
        )


@app.route("/add_assessment", methods=["GET", "POST"])
def add_assessment():
    title = "Add Assessment"
    pagename = "add_assessment"

    if request.method == "GET":
        return render_template("add_assessment.html", pagename=pagename, title=title)

    else:
        # get form data
        name = request.form["name"]
        assessment_type = request.form["type"]

        # assignemnt case
        if assessment_type == "assignment":

            # get form data
            weight = request.form["weight"]
            topic = request.form["topic"]
            handout = request.form["handout"]
            solution = request.form["solutions"]
            due_date = request.form["date"]

            assignment_tuple = (name, due_date, weight, topic, handout, solution)
            response = add_assignment(assignment_tuple)

            if response["success"]:
                flash("Assignment added!")
                return render_template(
                    "add_assessment.html", pagename=pagename, title=title
                )

            return render_template(
                "add_assessment.html",
                pagename=pagename,
                error=response["message"],
                title=title,
            )

        # adding test
        elif assessment_type == "test":
            # get form data
            location = request.form["location"]
            content = request.form["content"]
            due_date = request.form["test_date"]
            weight = request.form["test_weight"]

            test_tuple = (name, due_date, weight, location, content)
            response = add_test(test_tuple)

            if response["success"]:
                flash("Test added!")
                return render_template(
                    "add_assessment.html", pagename=pagename, title=title
                )

            return render_template(
                "add_assessment.html",
                pagename=pagename,
                error=response["message"],
                title=title,
            )

        elif assessment_type == "lab":
            # get form data
            topic = request.form["lab_topic"]
            handout = request.form["handout"]
            solution = request.form["solutions"]

            lab_tuple = (name, topic, handout, solution)
            response = add_lab(lab_tuple)

            if response["success"]:
                flash("Lab added!")
                return render_template(
                    "add_assessment.html", pagename=pagename, title=title
                )

            return render_template(
                "add_assessment.html",
                pagename=pagename,
                error=response["message"],
                title=title,
            )

        # rerender the page if neither type
        return render_template("add_assessment.html", pagename=pagename, title=title)


@app.route("/login", methods=["GET", "POST"])
def login():
    title = "Login"
    pagename = "login"

    if request.method == "GET":
        if "name" in session:
            flash("You Already logged in!")
            return redirect(url_for("home"))

        else:
            return render_template("login.html", pagename=pagename, title=title)

    else:
        # get form data
        username = request.form["Username"]
        password = request.form["Password"]

        # fetch person
        person = Person.query.filter_by(username=username).first()

        # cant log in
        if not person or not bcrypt.check_password_hash(person.password, password):
            flash("Please check your login details and try again.", "error")
            return render_template("login.html", pagename=pagename, title=title)
        else:
            # logged in, set session details
            user_type = person.user_type
            session["name"] = username
            session["user_type"] = user_type
            session.permanent = True
            return redirect(url_for("home"))


@app.route("/logout")
def logout():
    # reset session
    session.pop("name", default=None)
    session.pop("user_type", default=None)
    return redirect(url_for("home"))


# handle page not found errors
@app.errorhandler(404)
def _404(e):
    return render_template("error.html", pagename="error", error=e, title="Error")


if __name__ == "__main__":
    app.run(debug=True)
